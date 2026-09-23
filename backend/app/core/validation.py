import re
from datetime import date

import phonenumbers
from email_validator import EmailNotValidError, validate_email as _validate_email

NAME_PATTERN = re.compile(r"^[A-Za-z .'-]{1,50}$")
FULL_NAME_PATTERN = re.compile(r"^[A-Za-z .'-]{1,100}$")
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z ()-]{2,50}$")
INSURANCE_MEMBER_ID_PATTERN = re.compile(r"^[A-Z0-9]{1,30}$")
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

# Canonical values for `sex`, exactly as the field spec lists them, plus the
# spoken variants a caller is likely to use for each.
SEX_VALUES = ("Male", "Female", "Other", "Decline to Answer")
SEX_SYNONYMS: dict[str, str] = {
    "male": "Male",
    "m": "Male",
    "man": "Male",
    "female": "Female",
    "f": "Female",
    "woman": "Female",
    "other": "Other",
    "decline to answer": "Decline to Answer",
    "decline": "Decline to Answer",
    "declined": "Decline to Answer",
    "prefer not to say": "Decline to Answer",
    "prefer not to answer": "Decline to Answer",
}

# USPS state/territory codes plus full-name -> code mapping so callers can say
# either "Texas" or "T-X" and both are accepted.
STATE_NAMES: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "american samoa": "AS", "guam": "GU", "northern mariana islands": "MP",
    "puerto rico": "PR", "u.s. virgin islands": "VI", "virgin islands": "VI",
}
US_STATE_CODES = set(STATE_NAMES.values())

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

MAX_AGE_YEARS = 120


class ValidationError(ValueError):
    """Raised with a short, speakable, field-specific message."""


def normalize_name(value: str, field_label: str) -> str:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not trimmed:
        raise ValidationError(f"I need a {field_label} to continue.")
    if not NAME_PATTERN.match(trimmed):
        raise ValidationError(
            f"The {field_label} can only have letters, spaces, hyphens, "
            f"apostrophes, and periods."
        )
    return trimmed


def parse_date_of_birth(value: str) -> str:
    text = (value or "").strip()
    parsed: date | None = None

    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        pass

    if parsed is None:
        match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
        if match:
            month, day, year = (int(g) for g in match.groups())
            try:
                parsed = date(year, month, day)
            except ValueError:
                parsed = None

    if parsed is None:
        match = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", text)
        if match:
            month_name, day, year = match.groups()
            month = MONTHS.get(month_name.lower())
            if month is not None:
                try:
                    parsed = date(int(year), month, int(day))
                except ValueError:
                    parsed = None

    if parsed is None:
        raise ValidationError("I didn't catch a valid date of birth. Could you repeat it?")

    today = date.today()
    if parsed > today:
        raise ValidationError("The date of birth can't be in the future.")

    age_years = (today - parsed).days / 365.25
    if age_years > MAX_AGE_YEARS:
        raise ValidationError("That date of birth doesn't look right. Could you repeat it?")

    return parsed.isoformat()


def normalize_sex(value: str) -> str:
    normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
    canonical = SEX_SYNONYMS.get(normalized)
    if canonical is None:
        raise ValidationError(
            "Sex needs to be male, female, other, or decline to answer."
        )
    return canonical


def normalize_phone(value: str, field_label: str = "phone number") -> str:
    """Returns the 10-digit U.S. number, digits only (e.g. "5125550123")."""
    message = f"That {field_label} doesn't look valid. It needs to be a 10 digit U.S. number."
    try:
        parsed = phonenumbers.parse(value or "", "US")
    except phonenumbers.NumberParseException as exc:
        raise ValidationError(message) from exc
    if parsed.country_code != 1 or not phonenumbers.is_valid_number(parsed):
        raise ValidationError(message)
    national = str(parsed.national_number)
    if len(national) != 10:
        raise ValidationError(message)
    return national


def normalize_state(value: str) -> str:
    text = (value or "").strip()
    upper = text.upper()
    if upper in US_STATE_CODES:
        return upper
    mapped = STATE_NAMES.get(text.lower())
    if mapped:
        return mapped
    raise ValidationError("The state needs to be a valid U.S. state or territory.")


def normalize_zip(value: str) -> str:
    text = (value or "").strip()
    if not ZIP_PATTERN.match(text):
        raise ValidationError("The ZIP code needs to be 5 digits, or 5 digits plus 4.")
    return text


def normalize_email(value: str) -> str:
    try:
        result = _validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValidationError("That email address doesn't look valid.") from exc
    return result.normalized


def normalize_city(value: str) -> str:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not (1 <= len(trimmed) <= 100):
        raise ValidationError("The city needs to be between 1 and 100 characters.")
    return trimmed


def normalize_address_line(value: str, field_label: str, required: bool) -> str | None:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not trimmed:
        if required:
            raise ValidationError(f"I need a {field_label} to continue.")
        return None
    if len(trimmed) > 200:
        raise ValidationError(f"The {field_label} is too long.")
    return trimmed


def normalize_member_id(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        raise ValidationError("I need a member ID to continue.")
    return digits


def normalize_full_name(value: str, field_label: str) -> str:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not trimmed:
        raise ValidationError(f"I need the {field_label} to continue.")
    if not FULL_NAME_PATTERN.match(trimmed):
        raise ValidationError(
            f"The {field_label} can only have letters, spaces, hyphens, "
            f"apostrophes, and periods."
        )
    return trimmed


def normalize_insurance_provider(value: str) -> str:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not (1 <= len(trimmed) <= 100):
        raise ValidationError(
            "The insurance company name needs to be between 1 and 100 characters."
        )
    return trimmed


def normalize_insurance_member_id(value: str) -> str:
    """Callers read IDs out with pauses and dashes ("W 1 2 3 - 4 5"); keep only
    the letters and digits, upper-cased."""
    compact = re.sub(r"[\s-]", "", value or "").upper()
    if not INSURANCE_MEMBER_ID_PATTERN.match(compact):
        raise ValidationError(
            "The insurance member ID can only have letters and numbers."
        )
    return compact


def normalize_language(value: str) -> str:
    trimmed = re.sub(r"\s+", " ", (value or "").strip())
    if not LANGUAGE_PATTERN.match(trimmed):
        raise ValidationError("I didn't catch a valid preferred language.")
    return trimmed[0].upper() + trimmed[1:]
