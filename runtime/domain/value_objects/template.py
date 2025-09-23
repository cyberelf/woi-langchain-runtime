"""Template value objects - Pure domain models."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ConfigFieldValidation:
    """Configuration field validation rules value object.

    Immutable value object representing validation constraints for a template configuration field.
    No framework dependencies - pure domain concept.
    """

    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    enum_values: Optional[list[str]] = None

    def __post_init__(self):
        """Validate the validation rules themselves."""
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("min_length must be non-negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length must be non-negative")
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("min_length cannot be greater than max_length")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value cannot be greater than max_value")
        if self.enum_values is not None and not isinstance(self.enum_values, list):
            raise ValueError("enum_values must be a list")

    def has_constraints(self) -> bool:
        """Check if any validation constraints are defined."""
        return any(
            [
                self.min_length is not None,
                self.max_length is not None,
                self.min_value is not None,
                self.max_value is not None,
                self.pattern is not None,
                self.enum_values is not None,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        result = {}
        if self.min_length is not None:
            result["minLength"] = self.min_length
        if self.max_length is not None:
            result["maxLength"] = self.max_length
        if self.min_value is not None:
            result["min"] = self.min_value
        if self.max_value is not None:
            result["max"] = self.max_value
        if self.pattern is not None:
            result["pattern"] = self.pattern
        if self.enum_values is not None:
            result["enum"] = self.enum_values
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigFieldValidation":
        """Create ConfigFieldValidation from dictionary representation."""
        return cls(
            min_length=data.get("minLength"),
            max_length=data.get("maxLength"),
            min_value=data.get("min"),
            max_value=data.get("max"),
            pattern=data.get("pattern"),
            enum_values=data.get("enum"),
        )


@dataclass(frozen=True)
class ConfigField:
    """Template configuration field value object.

    Immutable value object representing a single configuration field for a template.
    No framework dependencies - pure domain concept.
    """

    key: str
    field_type: str
    description: Optional[str] = None
    default_value: Optional[Any] = None
    validation: Optional[ConfigFieldValidation] = None

    def __post_init__(self):
        """Validate the configuration field."""
        if not self.key:
            raise ValueError("Config field key cannot be empty")
        if not isinstance(self.key, str):
            raise ValueError("Config field key must be a string")
        if not self.field_type:
            raise ValueError("Config field type cannot be empty")
        if not isinstance(self.field_type, str):
            raise ValueError("Config field type must be a string")
        if self.validation is not None and not isinstance(self.validation, ConfigFieldValidation):
            raise ValueError("Validation must be a ConfigFieldValidation instance")

    def has_default(self) -> bool:
        """Check if this field has a default value."""
        return self.default_value is not None

    def has_validation(self) -> bool:
        """Check if this field has validation rules."""
        return self.validation is not None and self.validation.has_constraints()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        result: dict[str, Any] = {"key": self.key, "type": self.field_type}

        if self.description is not None:
            result["description"] = self.description

        if self.default_value is not None:
            result["default"] = self.default_value

        if self.validation is not None and self.validation.has_constraints():
            result["validation"] = self.validation.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigField":
        """Create ConfigField from dictionary representation."""
        validation = None
        if "validation" in data:
            validation = ConfigFieldValidation.from_dict(data["validation"])

        return cls(
            key=data["key"],
            field_type=data["type"],
            description=data.get("description"),
            default_value=data.get("default"),
            validation=validation,
        )

    @classmethod
    def create_string_field(
        cls,
        key: str,
        description: Optional[str] = None,
        default: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ) -> "ConfigField":
        """Create a string configuration field."""
        validation = None
        if any([min_length is not None, max_length is not None, pattern is not None]):
            validation = ConfigFieldValidation(min_length=min_length, max_length=max_length, pattern=pattern)

        return cls(
            key=key,
            field_type="string",
            description=description,
            default_value=default,
            validation=validation,
        )

    @classmethod
    def create_number_field(
        cls,
        key: str,
        description: Optional[str] = None,
        default: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> "ConfigField":
        """Create a number configuration field."""
        validation = None
        if any([min_value is not None, max_value is not None]):
            validation = ConfigFieldValidation(min_value=min_value, max_value=max_value)

        return cls(
            key=key,
            field_type="number",
            description=description,
            default_value=default,
            validation=validation,
        )

    @classmethod
    def create_enum_field(
        cls,
        key: str,
        enum_values: list[str],
        description: Optional[str] = None,
        default: Optional[str] = None,
    ) -> "ConfigField":
        """Create an enum configuration field."""
        validation = ConfigFieldValidation(enum_values=enum_values)

        return cls(
            key=key,
            field_type="string",
            description=description,
            default_value=default,
            validation=validation,
        )


@dataclass(frozen=True)
class TemplateInfo:
    """Template information value object.

    Immutable value object representing complete template metadata and configuration.
    No framework dependencies - pure domain concept.
    """

    # System-defined fields
    id: str
    framework: str

    # Protocol-defined fields
    name: str
    description: str
    version: str
    config_fields: list[ConfigField] = field(default_factory=list)

    def __post_init__(self):
        """Validate the template information."""
        if not self.id:
            raise ValueError("Template ID cannot be empty")
        if not isinstance(self.id, str):
            raise ValueError("Template ID must be a string")
        if not self.framework:
            raise ValueError("Framework cannot be empty")
        if not isinstance(self.framework, str):
            raise ValueError("Framework must be a string")
        if not self.name:
            raise ValueError("Template name cannot be empty")
        if not isinstance(self.name, str):
            raise ValueError("Template name must be a string")
        if not self.description:
            raise ValueError("Template description cannot be empty")
        if not isinstance(self.description, str):
            raise ValueError("Template description must be a string")
        if not self.version:
            raise ValueError("Template version cannot be empty")
        if not isinstance(self.version, str):
            raise ValueError("Template version must be a string")
        if not isinstance(self.config_fields, list):
            raise ValueError("Config fields must be a list")
        for field_obj in self.config_fields:
            if not isinstance(field_obj, ConfigField):
                raise ValueError("All config fields must be ConfigField instances")

    def has_config_fields(self) -> bool:
        """Check if this template has any configuration fields."""
        return len(self.config_fields) > 0

    def get_config_field_keys(self) -> list[str]:
        """Get list of configuration field keys."""
        return [field.key for field in self.config_fields]

    def get_config_field_by_key(self, key: str) -> Optional[ConfigField]:
        """Get a configuration field by its key."""
        for field in self.config_fields:
            if field.key == key:
                return field
        return None

    def get_required_config_fields(self) -> list[ConfigField]:
        """Get list of configuration fields that don't have default values."""
        return [field for field in self.config_fields if not field.has_default()]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        return {
            "id": self.id,
            "framework": self.framework,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "config": [field.to_dict() for field in self.config_fields],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateInfo":
        """Create TemplateInfo from dictionary representation."""
        config_fields = []
        for field_data in data.get("config", []):
            config_fields.append(ConfigField.from_dict(field_data))

        return cls(
            id=data["id"],
            framework=data["framework"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            config_fields=config_fields,
        )

    @classmethod
    def create_langgraph_template(
        cls,
        id: str,
        name: str,
        description: str,
        version: str,
        config_fields: Optional[list[ConfigField]] = None,
    ) -> "TemplateInfo":
        """Create a LangGraph template info."""
        return cls(
            id=id,
            framework="langgraph",
            name=name,
            description=description,
            version=version,
            config_fields=config_fields or [],
        )

    def __str__(self) -> str:
        """String representation."""
        config_count = len(self.config_fields)
        return f"TemplateInfo(id='{self.id}', name='{self.name}', framework='{self.framework}', config_fields={config_count})"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"TemplateInfo(id='{self.id}', framework='{self.framework}', "
            f"name='{self.name}', version='{self.version}', config_fields={len(self.config_fields)})"
        )
