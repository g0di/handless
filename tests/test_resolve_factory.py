from collections.abc import Callable, Iterator
from contextlib import nullcontext
from typing import TypedDict

import pytest

from handless import Container, LifetimeLiteral, Registry, Scope
from tests.helpers import (
    FakeContextManager,
    FakeService,
    FakeServiceWithParams,
    IFakeService,
    UntypedService,
    fake_service_factory_with_params,
    untyped_function,
    untyped_lambda,
)


class FactoryOptions(TypedDict, total=False):
    enter: bool
    lifetime: LifetimeLiteral


@pytest.mark.parametrize(
    "untyped_callable", [untyped_function, untyped_lambda, UntypedService]
)
def test_register_factory_raise_an_error_for_untyped_callable(
    registry: Registry, untyped_callable: Callable[..., object]
) -> None:
    with pytest.raises(TypeError):
        registry.bind(object).to_factory(untyped_callable)


class TestResolveFactory:
    @pytest.mark.parametrize(
        "factory", [FakeService, lambda: FakeService()], ids=["Type", "Function"]
    )
    def test_resolve_factory_calls_and_returns_factory_result(
        self,
        registry: Registry,
        container: Container,
        factory: Callable[..., FakeService],
    ) -> None:
        registry.bind(IFakeService).to_factory(factory)  # type: ignore[type-abstract]

        resolved = container.get(IFakeService)  # type: ignore[type-abstract]

        assert isinstance(resolved, FakeService)

    @pytest.mark.parametrize(
        "factory",
        [FakeServiceWithParams, fake_service_factory_with_params],
        ids=["Type", "Function"],
    )
    def test_resolve_factory_with_params_resolve_its_params_before_calling_the_factory(
        self,
        registry: Registry,
        container: Container,
        factory: Callable[..., FakeServiceWithParams],
    ) -> None:
        registry.bind(str).to_value("Hello World!")
        registry.bind(int).to_value(42)
        registry.bind(FakeServiceWithParams).to_factory(factory)

        received = container.get(FakeServiceWithParams)

        assert received == FakeServiceWithParams("Hello World!", 42)


class TestResolveFactoryContextManager:
    def test_resolve_factory_enters_and_returns_context_manager_enter_result(
        self, registry: Registry, container: Container
    ) -> None:
        cm = FakeContextManager(FakeService())
        registry.bind(FakeService).to_factory(lambda: cm)

        received = container.get(FakeService)

        assert received is cm.enter_result
        assert cm.entered
        assert not cm.exited

    def test_resolve_factory_wraps_generators_as_context_manager(
        self, registry: Registry, container: Container
    ) -> None:
        expected = FakeService()

        def fake_service_generator() -> Iterator[FakeService]:
            yield expected

        registry.bind(FakeService).to_factory(fake_service_generator)

        received = container.get(FakeService)

        assert received is expected

    def test_register_factory_not_enter_context_manager_if_enter_is_false(
        self, registry: Registry, container: Container
    ) -> None:
        registry.bind(FakeService).to_factory(lambda: FakeService(), enter=False)

        received = container.get(FakeService)

        assert not received.entered
        assert not received.exited

    def test_register_factory_with_context_manager_not_being_instance_of_registered_type_disallow_enter_to_be_false(
        self, registry: Registry
    ) -> None:
        # This test just ensure type checking
        registry.bind(str).to_factory(
            lambda: nullcontext("Hello World!"),  # type: ignore[arg-type, return-value]
            enter=False,
        )


class TestResolveTransientFactory:
    @pytest.fixture(autouse=True, name="resolved")
    def resolve_transient_factory(
        self, registry: Registry, container: Container
    ) -> FakeService:
        registry.bind(FakeService).to_factory(
            lambda: FakeService(), lifetime="transient"
        )

        return container.get(FakeService)

    def test_resolve_always_calls_and_returns_factory_result(
        self, container: Container, resolved: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is not resolved
        assert another.entered
        assert not another.exited

    def test_scope_resolve_always_calls_and_returns_factory_result(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        another1 = scope.get(FakeService)
        another2 = scope.get(FakeService)

        assert another1 is not resolved
        assert another2 is not resolved
        assert another1.entered
        assert another2.entered
        assert not another1.exited
        assert not another2.exited

    def test_container_close_exits_transient_context_managers(
        self, container: Container, resolved: FakeService
    ) -> None:
        another = container.get(FakeService)

        container.close()

        assert another.exited
        assert resolved.exited

    def test_scope_close_exits_transient_context_managers(self, scope: Scope) -> None:
        another1 = scope.get(FakeService)
        another2 = scope.get(FakeService)

        scope.close()

        assert another1.exited
        assert another2.exited

    def test_scope_close_not_exit_container_transient_context_managers(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert not resolved.exited


class TestResolveSingletonFactory:
    @pytest.fixture(autouse=True, name="resolved")
    def resolve_singleton_factory(
        self, registry: Registry, container: Container
    ) -> FakeService:
        registry.bind(FakeService).to_factory(
            lambda: FakeService(), lifetime="singleton"
        )

        return container.get(FakeService)

    def test_next_resolve_returns_cached_factory_result(
        self, container: Container, resolved: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is resolved

    def test_next_resolve_not_reenter_cached_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.get(FakeService)

        assert not resolved.reentered

    def test_next_resolve_not_exit_cached_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.get(FakeService)

        assert not resolved.exited

    def test_scope_resolve_returns_container_cached_factory_result(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        another = scope.get(FakeService)

        assert another is resolved

    def test_close_container_exits_cached_factory_result_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.close()

        assert resolved.exited

    def test_close_container_clear_cached_factory_result(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.close()

        assert container.get(FakeService) is not resolved

    def test_close_scope_not_exit_cached_factory_result_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert not resolved.exited

    def test_close_scope_not_clear_cached_factory_result_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert scope.get(FakeService) is resolved


class TestResolveScopedFactory:
    @pytest.fixture(autouse=True, name="resolved")
    def resolve_scoped_factory(
        self, registry: Registry, container: Container
    ) -> FakeService:
        registry.bind(FakeService).to_factory(lambda: FakeService(), lifetime="scoped")

        return container.get(FakeService)

    def test_next_resolve_returns_own_cached_factory_result(
        self, container: Container, resolved: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is resolved

    def test_next_resolve_not_reenter_own_cached_factory_result_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.get(FakeService)

        assert not resolved.reentered

    def test_next_resolve_not_exit_own_cached_factory_result_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.get(FakeService)

        assert not resolved.exited

    def test_scope_resolve_calls_cache_and_returns_own_factory_result(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        another1 = scope.get(FakeService)
        another2 = scope.get(FakeService)

        assert another1 is not resolved
        assert another1 is another2
        assert another1.entered
        assert not another1.exited
        assert not another1.reentered

    def test_close_container_exits_own_cached_factory_result_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.close()

        assert resolved.exited

    def test_close_container_clear_own_cached_factory_result(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.close()

        assert container.get(FakeService) is not resolved

    def test_close_scope_exits_own_cached_factory_result_context_manager(
        self, scope: Scope
    ) -> None:
        scoped = scope.get(FakeService)

        scope.close()

        assert scoped.exited

    def test_close_scope_clear_own_cached_factory_result(
        self, scope: Container
    ) -> None:
        scoped = scope.get(FakeService)

        scope.close()

        assert scope.get(FakeService) is not scoped

    def test_close_scope_not_exit_others_scoped_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert not resolved.exited
