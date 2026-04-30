import itertools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from unittest.mock import Mock, call

import pytest

from handless import Container, Scope, Scoped, Singleton, Transient
from handless.exceptions import ResolutionError
from handless.lifetimes import Lifetime
from tests.helpers import FakeService, FakeServiceWithParams


class FactoryRegistrationOptions(TypedDict, total=False):
    managed: bool
    lifetime: Lifetime


def test_resolve_type_calls_registration_factory_and_returns_its_result(
    container: Container, scope: Scope
) -> None:
    expected = FakeService()
    factory = Mock(return_value=expected)
    container.bind(FakeService).to_factory(factory)

    resolved = scope.resolve(FakeService)

    assert resolved is expected
    factory.assert_called_once()


def test_resolve_type_calls_registration_factory_with_ctx_and_returns_its_result(
    container: Container, scope: Scope
) -> None:
    expected = FakeService()
    factory = Mock(wraps=lambda ctx: expected)  # noqa: ARG005
    container.bind(FakeService).to_factory(factory)

    resolved = scope.resolve(FakeService)

    assert resolved is expected
    factory.assert_called_once_with(ctx=scope)


def test_resolve_type_calls_registration_factory_with_dependencies_and_returns_its_result(
    container: Container, scope: Scope
) -> None:
    factory = Mock(wraps=FakeServiceWithParams)
    container.bind(FakeServiceWithParams).to_factory(factory)
    container.bind(str).to_value("foo")
    container.bind(int).to_value(42)

    resolved = scope.resolve(FakeServiceWithParams)

    assert isinstance(resolved, FakeServiceWithParams)
    factory.assert_called_once_with(foo="foo", bar=42)


@pytest.mark.parametrize(
    "options", [FactoryRegistrationOptions(), FactoryRegistrationOptions(managed=True)]
)
def test_resolve_type_enters_context_manager_returned_by_registration_factory(
    container: Container, scope: Scope, options: FactoryRegistrationOptions
) -> None:
    container.bind(FakeService).to_self(**options)

    resolved = scope.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_type_not_enter_context_manager_returned_by_registration_factory_when_managed_is_false(
    container: Container, scope: Scope
) -> None:
    container.bind(FakeService).to_self(managed=False)

    resolved = scope.resolve(FakeService)

    assert not resolved.entered


def test_resolve_type_not_enter_non_context_manager_object_returned_by_registration_factory(
    container: Container, scope: Scope
) -> None:
    container.bind(object).to_self(managed=True)

    try:
        scope.resolve(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


def test_resolve_error_exposes_resolution_chain_and_root_cause(
    container: Container, scope: Scope
) -> None:
    root_error = RuntimeError("broken dependency")

    class BrokenDependency:
        pass

    class IntermediateDependency:
        def __init__(self, dependency: BrokenDependency) -> None:
            self.dependency = dependency

    class RootService:
        def __init__(self, dependency: IntermediateDependency) -> None:
            self.dependency = dependency

    def create_broken_dependency() -> BrokenDependency:
        raise root_error

    container.bind(RootService).to_self()
    container.bind(IntermediateDependency).to_self()
    container.bind(BrokenDependency).to_factory(create_broken_dependency)

    with pytest.raises(ResolutionError) as error_info:
        scope.resolve(RootService)

    error = error_info.value

    assert error.outer_type is RootService
    assert error.inner_type is BrokenDependency
    assert error.resolution_chain == (
        RootService,
        IntermediateDependency,
        BrokenDependency,
    )
    assert error.root_cause is error.__cause__ is root_error


class TestContainerResolveShortcut:
    def test_resolves_type_without_manual_scope(self, container: Container) -> None:
        expected = object()
        container.bind(object).to_value(expected)

        with container.resolve(object) as resolved:
            assert resolved is expected

    def test_uses_new_scope_for_each_call(self, container: Container) -> None:
        container.bind(FakeService).to_self(Scoped())

        with container.resolve(FakeService) as first:
            pass

        with container.resolve(FakeService) as second:
            pass

        assert first is not second

    def test_releases_temporary_scope(self, container: Container) -> None:
        container.bind(FakeService).to_self(Scoped())

        with container.resolve(FakeService) as resolved:
            assert resolved.entered
            assert not resolved.exited

        assert resolved.exited

    def test_resolves_several_types_in_single_call(self, container: Container) -> None:
        expected_number = 42
        container.bind(str).to_value("foo")
        container.bind(int).to_value(expected_number)

        with container.resolve(str, int) as (text, number):
            assert text == "foo"
            assert number == expected_number

    def test_resolve_several_types_keeps_temporary_scope_alive(
        self, container: Container
    ) -> None:
        expected_number = 42
        container.bind(FakeService).to_self(Scoped())
        container.bind(int).to_value(expected_number)

        with container.resolve(FakeService, int) as (service, number):
            assert number == expected_number
            assert service.entered
            assert not service.exited

        assert service.exited


class TestResolveTypeUsingTransientLifetime:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(
        autouse=True,
        params=[
            FactoryRegistrationOptions(),
            FactoryRegistrationOptions(lifetime=Transient()),
        ],
    )
    def resolved(
        self,
        request: pytest.FixtureRequest,
        container: Container,
        scope: Scope,
        factory: Mock,
    ) -> FakeService:
        container.bind(FakeService).to_factory(factory, **request.param)

        return scope.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_on_each_resolve(
        self, resolved: FakeService, scope: Scope, factory: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=scope), call(_=scope)])

    def test_calls_and_returns_registration_factory_result_on_different_scope(
        self, resolved: FakeService, container: Container, scope: Scope, factory: Mock
    ) -> None:
        with container.create_scope() as scope2:
            received = scope2.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=scope), call(_=scope2)])

    def test_release_scope_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        another = scope.resolve(FakeService)

        scope.close()

        assert resolved.exited
        assert another.exited


class TestResolveTypeBoundToSingletonRegistration:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture
    def resolved(
        self, container: Container, scope: Scope, factory: Mock
    ) -> FakeService:
        container.bind(FakeService).to_factory(factory, Singleton())

        return scope.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_once_per_scope(
        self, resolved: FakeService, scope: Scope, factory: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=scope)

    def test_calls_and_returns_registration_factory_result_once_per_container(
        self, resolved: FakeService, container: Container, scope: Scope, factory: Mock
    ) -> None:
        with container.create_scope() as scope2:
            received = scope2.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=scope)

    def test_resolve_singleton_is_threadsafe(self, container: Container) -> None:
        def _factory(ctx: Scope) -> FakeServiceWithParams:
            # Small sleep to force threads context switch
            time.sleep(0.01)
            return FakeServiceWithParams(ctx.resolve(str), ctx.resolve(int))

        mock = Mock(wraps=_factory)
        container.bind(str).to_value("foo")
        container.bind(int).to_value(42)
        container.bind(FakeService).to_factory(mock, Singleton())

        with ThreadPoolExecutor(100) as pool:
            results = pool.map(
                lambda _: container.create_scope().resolve(FakeService), range(100)
            )

        mock.assert_called_once()
        assert len(set(results)) == 1

    def test_release_scope_not_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert not resolved.exited

    def test_release_container_exit_entered_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.close()

        assert resolved.exited

    def test_release_container_clear_cached_value(
        self, container: Container, scope: Scope, resolved: FakeService
    ) -> None:
        container.close()

        received = scope.resolve(FakeService)

        assert received is not resolved

    def test_release_scope_not_clear_cached_value(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        received = scope.resolve(FakeService)

        assert received is resolved


class TestResolveTypeBoundToScopeRegistration:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, container: Container, scope: Scope, factory: Mock
    ) -> FakeService:
        container.bind(FakeService).to_factory(factory, Scoped())

        return scope.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_once_per_scope(
        self, resolved: FakeService, scope: Scope, factory: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=scope)

    def test_calls_and_returns_registration_factory_result_on_different_scope(
        self, resolved: FakeService, container: Container, scope: Scope, factory: Mock
    ) -> None:
        with container.create_scope() as scope2:
            received = scope2.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=scope), call(_=scope2)])

    def test_release_scope_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        assert resolved.exited

    def test_release_scope_clear_cached_value(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.close()

        received = scope.resolve(FakeService)

        assert received is not resolved


class TestOverrideTypes:
    @pytest.fixture
    def factory(self, container: Container) -> Mock:
        factory = Mock(wraps=FakeService)
        container.bind(FakeService).to_factory(factory)
        return factory

    @pytest.fixture
    def factory_override(self, container: Container) -> Mock:
        factory_override = Mock(wraps=FakeService)
        container.override(FakeService).to_factory(factory_override)
        return factory_override

    def test_resolve_type_calls_override_factory_and_returns_its_result_when_registered(
        self, scope: Scope, factory: Mock, factory_override: Mock
    ) -> None:
        resolved = scope.resolve(FakeService)

        assert isinstance(resolved, FakeService)
        factory_override.assert_called_once_with()
        factory.assert_not_called()

    def test_release_container_clear_overrides(
        self, container: Container, scope: Scope, factory: Mock, factory_override: Mock
    ) -> None:
        container.close()
        scope.resolve(FakeService)

        factory.assert_called_once_with()
        factory_override.assert_not_called()

    def test_override_can_override_an_already_overridden_type(
        self, container: Container, scope: Scope, factory: Mock, factory_override: Mock
    ) -> None:
        factory_override2 = Mock(wraps=FakeService)
        container.override(FakeService).to_factory(factory_override2)

        scope.resolve(FakeService)

        factory.assert_not_called()
        factory_override.assert_not_called()
        factory_override2.assert_called_once_with()

    @pytest.mark.parametrize(
        ("lifetime", "override_lifetime"),
        [
            # Ensure that whatever lifetimes are used, override always takes precedence
            *itertools.permutations([Transient(), Scoped(), Singleton()], 2),
            (Transient(), Transient()),
            (Singleton(), Singleton()),
            (Scoped(), Scoped()),
        ],
    )
    def test_override_a_cached_type_returns_override_result(
        self,
        container: Container,
        scope: Scope,
        lifetime: Lifetime,
        override_lifetime: Lifetime,
    ) -> None:
        factory = Mock(wraps=FakeService)
        factory_override = Mock(wraps=FakeService)
        container.bind(FakeService).to_factory(factory, lifetime)
        singleton = scope.resolve(FakeService)

        container.override(FakeService).to_factory(
            factory_override, lifetime=override_lifetime
        )

        override = scope.resolve(FakeService)
        assert override is not singleton


class TestContainerCloseWithScopes:
    def test_container_close_closes_referenced_scopes(
        self, container: Container
    ) -> None:
        """Verify that container.close() closes all referenced scopes."""
        container.bind(FakeService).to_self(lifetime=Singleton())
        scope = container.create_scope()
        service = scope.resolve(FakeService)

        assert service.entered
        assert not service.exited

        container.close()

        assert service.exited

    def test_container_close_no_error_when_unreferenced_scopes_garbage_collected(
        self, container: Container
    ) -> None:
        """Verify container.close() handles scopes that are garbage collected (weakref).

        When a scope is no longer referenced and garbage collected, it should
        automatically disappear from the container's weakref set, and closing
        the container should not raise any errors.
        """
        import gc

        container.bind(FakeService).to_self(lifetime=Singleton())

        def create_unreferenced_scope_and_resolve_service() -> FakeService:
            scope = container.create_scope()
            return scope.resolve(FakeService)

        service = create_unreferenced_scope_and_resolve_service()
        gc.collect()

        container.close()

        assert service.exited
