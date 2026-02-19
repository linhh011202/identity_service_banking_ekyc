from dependency_injector import containers, providers

from app.core.config import configs
from app.core.database import Database
from app.repository import UserRepository
from app.service import UserService
from app.service.ekyc_service import EkycService
from app.service.pubsub_service import PubsubService


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

    user_service = providers.Factory(UserService, user_repository=user_repository)

    ekyc_service = providers.Factory(EkycService, user_repository=user_repository)

    pubsub_service = providers.Singleton(PubsubService)
