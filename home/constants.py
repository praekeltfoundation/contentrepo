# Define constants for use throughout the application
from types import MappingProxyType

GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("non-binary", "Non-Binary"),
    ("empty", "Rather Not Say/Empty"),
]

AGE_CHOICES = [
    ("15-18", "15-18"),
    ("19-24", "19-24"),
    ("empty", "Empty"),
]

RELATIONSHIP_STATUS_CHOICES = [
    ("in_a_relationship", "In a Relationship"),
    ("single", "Single"),
    ("complicated", "It's Complicated"),
    ("empty", "Empty"),
]

# MappingProxyType is read-only. (Mutable constants make me sad.)
# FIXME: Add more language mappings here?
WHATSAPP_LANGUAGE_MAPPING = MappingProxyType(
    {
        "en": "en_US",  # FIXME: Do we need to keep this for backcompat?
        "pt": "pt_PT",  # FIXME: Should this perhaps be pt_BR instead?
    }
)
