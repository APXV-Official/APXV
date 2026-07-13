"""Curated probe strings — one representative input per compiled APX pattern."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional


@dataclass(frozen=True)
class PatternProbe:
    pattern_type: str
    input_text: str
    secret: str
    description: str = ""
    also_accepts: FrozenSet[str] = field(default_factory=frozenset)


PATTERN_PROBES: List[PatternProbe] = [
    PatternProbe("email_address", "Contact alice.wonder@example.com today.", "alice.wonder@example.com"),
    PatternProbe("ssn", "SSN: 123-45-6789 on file.", "123-45-6789"),
    PatternProbe("ssn_last4", "Record shows ssn_last4: 6789.", "ssn_last4: 6789"),
    PatternProbe("credit_card_dashed", "Card 4111-1111-1111-1111 on file.", "4111-1111-1111-1111"),
    PatternProbe("credit_card", "Payment card 4111111111111111.", "4111111111111111"),
    PatternProbe("iban", "Transfer to GB82WEST12345698765432.", "GB82WEST12345698765432"),
    PatternProbe("national_id_numbers", "National ID 123 456 789 listed.", "123 456 789"),
    PatternProbe("tax_id", "Employer EIN 12-3456789.", "12-3456789"),
    PatternProbe("bank_account", "Deposit to 1234-5678-9012-3456.", "1234-5678-9012-3456"),
    PatternProbe("routing_number", "Bank routing number 021000021.", "021000021"),
    PatternProbe("credit_card_generic", "Visa 4111 1111 1111 1111.", "4111 1111 1111 1111"),
    PatternProbe("account_number", "Checking account 12345678901234.", "12345678901234"),
    PatternProbe("cvv", "Card cvv: 456 entered.", "cvv: 456"),
    PatternProbe("ssn_fragment", "SSN ending in 6789 noted.", "ending in 6789"),
    PatternProbe("cc_fragment", "Visa card ending 1111.", "1111"),
    PatternProbe("crypto_wallet", "Send to 0x" + "a" * 40 + ".", "0x" + "a" * 40),
    PatternProbe("address", "Residence 123 Main Street Apt 2.", "123 Main Street"),
    PatternProbe("city_county_names", "Resident in Boston area.", "Boston"),
    PatternProbe("po_box", "Mailing P.O. Box 4455.", "P.O. Box 4455"),
    PatternProbe("state_abbreviation", "Mailing OR 97201 only.", "OR 97201"),
    PatternProbe("zip_code", "Postal code 90210 assigned.", "90210"),
    PatternProbe("month_abbrev_in_context", "Event logged jan 15, 2020.", "jan 15, 2020"),
    PatternProbe(
        "embedded_date_concat",
        "Log entry johndoe14february201623:14est.",
        "johndoe14february201623:14est",
    ),
    PatternProbe("date_of_birth", "DOB 01/15/1985 confirmed.", "01/15/1985"),
    PatternProbe("partial_dob", "partial DOB March 15 recorded.", "March 15"),
    PatternProbe("mrn", "Hospital MRN-12345678.", "MRN-12345678"),
    PatternProbe("birth_year", "born 1985 recorded.", "1985"),
    PatternProbe("date_spelled_month_with_year", "recorded January 15, 2020.", "January 15, 2020"),
    PatternProbe("date_spelled_month_noyear", "Follow-up February 3rd.", "February 3rd"),
    PatternProbe("date_spelled_month_day_first", "Visit 15th of January 2020.", "15th of January 2020"),
    PatternProbe("any_date_slash", "meeting 3/15/2024 scheduled.", "3/15/2024"),
    PatternProbe("any_date_dash", "timestamp 2024-03-15 logged.", "2024-03-15"),
    PatternProbe("date_dash_mdy", "Legacy date 03-15-2024.", "03-15-2024"),
    PatternProbe("name_with_credential", "chart johnsmith, rn end.", "johnsmith, rn"),
    PatternProbe("lowercase_name_credential", "Reviewer Alice, pharmd.", "Alice, pharmd"),
    PatternProbe("concatenated_name_suffix", "Footer addendumbyjohndoe.", "addendumbyjohndoe"),
    PatternProbe("policy_member_id", "Insurance member# HP987654321.", "HP987654321"),
    PatternProbe("member_id_formatted", "Plan Member ID: 4EG7-XY9-KL2M.", "4EG7-XY9-KL2M"),
    PatternProbe("name_after_title", "Referral Dr. Sarah Johnson.", "Dr. Sarah Johnson"),
    PatternProbe("embedded_name_date", "Note johnpon15january filed.", "johnpon15january"),
    PatternProbe("age_pattern", "Chart says 45 years old.", "45 years old"),
    PatternProbe("age_prefix", "Demographics age: 32.", "age: 32"),
    PatternProbe("age_compressed", "Pediatrics 20 y m noted.", "20 y m"),
    PatternProbe("ip_address", "Logged from 192.168.1.1.", "192.168.1.1"),
    PatternProbe("vehicle_vin", "Vehicle VIN: 1HGBH41JXMN109186.", "1HGBH41JXMN109186"),
    PatternProbe("vehicle_license_plate", "Parking plate: XY12Z9.", "XY12Z9"),
    PatternProbe("mac_address", "NIC AA:BB:CC:DD:EE:FF.", "AA:BB:CC:DD:EE:FF"),
    PatternProbe("web_url", "Portal https://example.com/records.", "https://example.com/records"),
    PatternProbe("tracking_token", "Analytics session abcdefghijklmnopqrst.", "abcdefghijklmnopqrst"),
    PatternProbe("photo_image_reference", "Attachment scan_001.jpg.", "scan_001.jpg"),
    PatternProbe("device_serial_number", "Pump serial SN123456789.", "SN123456789"),
    PatternProbe("biometric_identifiers", "On file fingerprint AB12CD34.", "fingerprint AB12CD34"),
    PatternProbe("genetic_marker", "Lab BRCA1 positive.", "BRCA1"),
    PatternProbe("phone_number", "Callback (555) 123-4567.", "555) 123-4567"),
    PatternProbe("fax_number", "Office fax: 555-987-6543.", "555-987-6543"),
    PatternProbe("certificate_license_number", "Board cert: ABC123456.", "ABC123456"),
    PatternProbe("city_state_zip_pattern", "Office Cambridge, MA 02138.", "Cambridge, MA 02138"),
    PatternProbe("city_state_pattern", "Office Dorchester, MA.", "Dorchester, MA"),
    PatternProbe("person_full_name", "patient: Jane Marie Smith seen.", "Jane Marie Smith"),
    PatternProbe(
        "full_name",
        "contact: Robert Johnson.",
        "Robert Johnson",
        also_accepts=frozenset({"person_full_name"}),
    ),
    PatternProbe("uppercase_name", "patient: JANE SMITH.", "JANE SMITH"),
    PatternProbe("standalone_alphanumeric_id", "Token 4EG7-XY9-KL2M issued.", "4EG7-XY9-KL2M"),
    PatternProbe("orphaned_last_name", "Note Alice [REDACTED-EMAIL] here.", "Alice [REDACTED-EMAIL]"),
    PatternProbe("age_sex_combo", "Chart 45 yo male.", "45 yo male"),
    PatternProbe("passport_number", "Travel passport AB1234567.", "AB1234567"),
    PatternProbe("drivers_license", "ID driver license MA-D9876543.", "MA-D9876543"),
    PatternProbe("bare_domain_url", "Site example.com referenced.", "example.com"),
    PatternProbe("gps_coordinates", "Last GPS 37.7749,-122.4194.", "37.7749,-122.4194"),
]