"""Small defensive helpers around DIgSILENT's dynamically typed API."""

from __future__ import annotations

from typing import Any, List, Optional

from pfemt.errors import PowerFactoryExecutionError


def has_attribute(obj: Any, name: str) -> bool:
    """Return whether a PowerFactory object exposes an attribute."""
    checker = getattr(obj, "HasAttribute", None)
    if callable(checker):
        try:
            return bool(checker(name))
        except Exception:
            return False
    return hasattr(obj, name)


def set_attribute(obj: Any, name: str, value: Any, required: bool = True) -> bool:
    """Set an attribute with a useful error when it is unavailable."""
    if not has_attribute(obj, name):
        if required:
            raise PowerFactoryExecutionError(
                "{} has no attribute {!r}".format(object_path(obj), name)
            )
        return False
    try:
        setter = getattr(obj, "SetAttribute", None)
        if callable(setter):
            setter(name, value)
        else:
            setattr(obj, name, value)
    except Exception as exc:
        if required:
            raise PowerFactoryExecutionError(
                "Cannot set {}.{}={!r}: {}".format(object_path(obj), name, value, exc)
            ) from exc
        return False
    return True


def object_path(obj: Any) -> str:
    """Return the full PowerFactory path when available."""
    getter = getattr(obj, "GetFullName", None)
    if callable(getter):
        try:
            return str(getter())
        except Exception:
            pass
    return str(getattr(obj, "loc_name", obj))


def contents(parent: Any, pattern: str) -> List[Any]:
    """Normalize GetContents output to a list."""
    result = parent.GetContents(pattern)
    return list(result or [])


def first(parent: Any, pattern: str, required: bool = True) -> Optional[Any]:
    """Return the first direct child matching a PowerFactory pattern."""
    matches = contents(parent, pattern)
    if matches:
        return matches[0]
    if required:
        raise PowerFactoryExecutionError(
            "Object {!r} not found below {}".format(pattern, object_path(parent))
        )
    return None


def create_or_get(parent: Any, class_name: str, name: str) -> Any:
    """Create an object unless a child with the same class and name exists."""
    existing = first(parent, "{}.{}".format(name, class_name), required=False)
    if existing is not None:
        return existing
    created = parent.CreateObject(class_name, name)
    if created is None:
        raise PowerFactoryExecutionError(
            "PowerFactory could not create {} {!r} below {}".format(
                class_name, name, object_path(parent)
            )
        )
    return created


def execute(command: Any, label: str) -> None:
    """Execute a PowerFactory command and enforce its return code."""
    code = command.Execute()
    if code not in (None, 0):
        raise PowerFactoryExecutionError("{} failed with return code {}".format(label, code))


def find_calc_objects(app: Any, pattern: str) -> List[Any]:
    """Get calculation-relevant objects using a full class/name pattern."""
    return list(app.GetCalcRelevantObjects(pattern) or [])


def unique_calc_object(app: Any, pattern: str) -> Any:
    """Resolve exactly one calculation-relevant object."""
    matches = find_calc_objects(app, pattern)
    if len(matches) != 1:
        raise PowerFactoryExecutionError(
            "Expected exactly one object for {!r}; found {}".format(pattern, len(matches))
        )
    return matches[0]

