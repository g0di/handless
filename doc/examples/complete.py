import smtplib
from dataclasses import dataclass
from typing import Protocol

from handless import Container, Contextual, ResolutionContext, Singleton, Transient


@dataclass
class User:
    email: str


@dataclass
class Config:
    smtp_host: str


class UserRepository(Protocol):
    def add(self, cat: User) -> None: ...
    def get(self, email: str) -> User | None: ...


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: list[User] = []

    def add(self, user: User) -> None:
        self._users.append(user)

    def get(self, email: str) -> User | None:
        for user in self._users:
            if user.email == email:
                return user
        return None


class NotificationManager(Protocol):
    def send(self, user: User, message: str) -> None: ...


class StdoutNotificationManager(NotificationManager):
    def send(self, user: User, message: str) -> None:
        print(f"{user.email} - {message}")  # noqa: T201


class EmailNotificationManager(NotificationManager):
    def __init__(self, smtp: smtplib.SMTP) -> None:
        self.server = smtp
        self.server.noop()

    def send(self, user: User, message: str) -> None:
        msg = f"Subject: My Service notification\n{message}"
        self.server.sendmail(
            from_addr="myservice@example.com", to_addrs=[user.email], msg=msg
        )


class UserService:
    def __init__(
        self, users: UserRepository, notifications: NotificationManager
    ) -> None:
        self.users = users
        self.notifications = notifications

    def create_user(self, email: str) -> None:
        user = User(email)
        self.users.add(user)
        self.notifications.send(user, "Your account has been created")

    def get_user(self, email: str) -> User:
        user = self.users.get(email)
        if not user:
            msg = f"There is no user with email {email}"
            raise ValueError(msg)
        return user


config = Config(smtp_host="test")

container = Container()
container.register(Config).value(config)

# User repository
container.register(InMemoryUserRepository).self(lifetime=Singleton())
container.register(UserRepository).alias(InMemoryUserRepository)  # type: ignore[type-abstract]

# Notification manager
container.register(smtplib.SMTP).factory(
    lambda ctx: smtplib.SMTP(ctx.resolve(Config).smtp_host),
    lifetime=Singleton(),
    enter=True,
)
container.register(StdoutNotificationManager).self(lifetime=Transient())
container.register(EmailNotificationManager).self()


@container.factory
def create_notification_manager(
    config: Config, ctx: ResolutionContext
) -> NotificationManager:
    if config.smtp_host == "stdout":
        return ctx.resolve(StdoutNotificationManager)
    return ctx.resolve(EmailNotificationManager)


# Top level service
container.register(UserService).self(lifetime=Contextual())


with container.open_context() as ctx:
    service = ctx.resolve(UserService)
    service.create_user("hello.world@handless.io")
    # hello.world@handless.io - Your account has been created
    print(service.get_user("hello.world@handless.io"))  # noqa: T201
    # User(email='hello.world@handless.io')  # noqa: ERA001


container.release()
