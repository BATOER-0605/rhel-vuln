from app.filter import matches_rhel
from app.schemas import FilterMode


def _entry(packages):
    return {"released_packages": packages}


class TestMatchesRhel:
    def test_minor_match_el8_4(self):
        entry = _entry(["openssl-1.1.1k-12.el8_4.x86_64"])
        assert matches_rhel(entry, 8, 4, FilterMode.minor) is True

    def test_minor_does_not_match_different_minor(self):
        entry = _entry(["openssl-1.1.1k-12.el8_6.x86_64"])
        assert matches_rhel(entry, 8, 4, FilterMode.minor) is False

    def test_minor_falls_back_to_generic_elX_when_no_other_minor_present(self):
        entry = _entry(["bash-5.1-8.el8.x86_64"])
        assert matches_rhel(entry, 8, 4, FilterMode.minor) is True

    def test_major_match_any_elX(self):
        entry = _entry(["kernel-4.18.0-553.16.1.el8_10.x86_64"])
        assert matches_rhel(entry, 8, None, FilterMode.major) is True

    def test_major_does_not_match_other_major(self):
        entry = _entry(["glibc-2.34-100.el9.x86_64"])
        assert matches_rhel(entry, 8, None, FilterMode.major) is False

    def test_no_packages_returns_false(self):
        assert matches_rhel({}, 8, 4, FilterMode.minor) is False
        assert matches_rhel({"released_packages": []}, 8, None, FilterMode.major) is False

    def test_minor_none_uses_major_logic(self):
        entry = _entry(["kernel-4.18.0-553.16.1.el8_10.x86_64"])
        assert matches_rhel(entry, 8, None, FilterMode.minor) is True

    def test_major_pattern_word_boundary(self):
        entry = _entry(["something-1.0.el80.x86_64"])  # el80, NOT el8
        assert matches_rhel(entry, 8, None, FilterMode.major) is False

    def test_rhel9_minor(self):
        entry = _entry(["nginx-1.22-1.el9_2.x86_64"])
        assert matches_rhel(entry, 9, 2, FilterMode.minor) is True
        assert matches_rhel(entry, 9, 4, FilterMode.minor) is False
