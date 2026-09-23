import pytest

from app.core.validation import (
    ValidationError,
    normalize_email,
    normalize_full_name,
    normalize_insurance_member_id,
    normalize_language,
    normalize_member_id,
    normalize_name,
    normalize_phone,
    normalize_sex,
    normalize_state,
    normalize_zip,
    parse_date_of_birth,
)


class TestName:
    def test_accepts_plain_name(self):
        assert normalize_name("Jane", "first name") == "Jane"

    def test_accepts_apostrophe_and_hyphen(self):
        assert normalize_name("O'Brien-Smith", "last name") == "O'Brien-Smith"

    def test_accepts_period_for_names_like_mcdonald(self):
        assert normalize_name("de la Cruz", "last name") == "de la Cruz"

    def test_collapses_inner_whitespace(self):
        assert normalize_name("Mary   Jane", "first name") == "Mary Jane"

    def test_does_not_force_title_case(self):
        assert normalize_name("McDonald", "last name") == "McDonald"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            normalize_name("", "first name")

    def test_rejects_digits(self):
        with pytest.raises(ValidationError):
            normalize_name("John3", "first name")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            normalize_name("a" * 51, "first name")


class TestDateOfBirth:
    def test_accepts_iso(self):
        assert parse_date_of_birth("1990-03-05") == "1990-03-05"

    def test_accepts_us_slash_format(self):
        assert parse_date_of_birth("03/05/1990") == "1990-03-05"

    def test_accepts_month_name_format(self):
        assert parse_date_of_birth("March 5, 1990") == "1990-03-05"

    def test_rejects_future_date(self):
        with pytest.raises(ValidationError):
            parse_date_of_birth("2999-01-01")

    def test_rejects_over_120_years_old(self):
        with pytest.raises(ValidationError):
            parse_date_of_birth("1850-01-01")

    def test_rejects_garbage(self):
        with pytest.raises(ValidationError):
            parse_date_of_birth("not a date")


class TestSex:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("male", "Male"),
            ("Female", "Female"),
            ("OTHER", "Other"),
            ("decline to answer", "Decline to Answer"),
            ("prefer not to say", "Decline to Answer"),
        ],
    )
    def test_maps_to_spec_values(self, value, expected):
        assert normalize_sex(value) == expected

    def test_rejects_unknown(self):
        with pytest.raises(ValidationError):
            normalize_sex("unspecified")


class TestPhone:
    def test_accepts_valid_us_number(self):
        assert normalize_phone("5125550123") == "5125550123"

    def test_accepts_number_with_formatting(self):
        assert normalize_phone("(512) 555-0123") == "5125550123"

    def test_accepts_country_code(self):
        assert normalize_phone("+1 512 555 0123") == "5125550123"

    def test_rejects_non_us_number(self):
        with pytest.raises(ValidationError):
            normalize_phone("+44 20 7946 0958")

    def test_rejects_too_short(self):
        with pytest.raises(ValidationError):
            normalize_phone("12345")

    def test_rejects_invalid_number(self):
        with pytest.raises(ValidationError):
            normalize_phone("0000000000")


class TestState:
    def test_accepts_code(self):
        assert normalize_state("TX") == "TX"

    def test_accepts_lowercase_code(self):
        assert normalize_state("tx") == "TX"

    def test_accepts_full_name(self):
        assert normalize_state("Texas") == "TX"

    def test_accepts_dc(self):
        assert normalize_state("District of Columbia") == "DC"

    def test_rejects_unknown(self):
        with pytest.raises(ValidationError):
            normalize_state("Atlantis")


class TestZip:
    def test_accepts_five_digit(self):
        assert normalize_zip("78701") == "78701"

    def test_accepts_zip_plus_four(self):
        assert normalize_zip("78701-1234") == "78701-1234"

    def test_rejects_too_short(self):
        with pytest.raises(ValidationError):
            normalize_zip("787")

    def test_rejects_letters(self):
        with pytest.raises(ValidationError):
            normalize_zip("ABCDE")


class TestEmail:
    def test_accepts_valid(self):
        assert normalize_email("jane@example.com") == "jane@example.com"

    def test_rejects_invalid(self):
        with pytest.raises(ValidationError):
            normalize_email("not-an-email")


class TestMemberId:
    def test_strips_non_digits(self):
        assert normalize_member_id("1234-5678") == "12345678"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            normalize_member_id("")


class TestOptionalFields:
    def test_insurance_member_id_compacts_spoken_form(self):
        assert normalize_insurance_member_id("xyz 123-456") == "XYZ123456"

    def test_insurance_member_id_rejects_symbols(self):
        with pytest.raises(ValidationError):
            normalize_insurance_member_id("ABC#123")

    def test_language_capitalized(self):
        assert normalize_language("spanish") == "Spanish"

    def test_language_rejects_digits(self):
        with pytest.raises(ValidationError):
            normalize_language("42")

    def test_full_name_allows_spaces(self):
        assert normalize_full_name("Mary  Jane Watson", "contact") == "Mary Jane Watson"
