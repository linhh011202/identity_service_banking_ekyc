from dependency_injector import containers, providers

from app.core.config import configs
from app.core.database import Database
from app.repository import UserFaceRepository, UserRepository
from app.service.user.user_service import UserService
from app.service.ekyc.ekyc_service import EkycService
from app.service.pubsub.pubsub_service import PubsubService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.v1.endpoints.user_endpoints",
            "app.api.v1.endpoints.ekyc_endpoints",
        ]
    )

    db = providers.Singleton(Database, db_url=configs.DATABASE_URL)

    user_repository = providers.Factory(
        UserRepository, session_factory=db.provided.session
    )

    user_face_repository = providers.Factory(
        UserFaceRepository, session_factory=db.provided.session
    )

    user_service = providers.Factory(UserService, user_repository=user_repository)

    pubsub_service = providers.Singleton(PubsubService)

    ekyc_service = providers.Factory(
        EkycService,
        user_repository=user_repository,
        user_face_repository=user_face_repository,
        pubsub_service=pubsub_service,
    )
