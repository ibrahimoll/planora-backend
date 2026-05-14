from urllib import parse

DICEBEAR_INITIALS_BASE_URL = "https://api.dicebear.com/9.x/initials/svg"


def build_default_profile_pic(full_name: str) -> str:
    seed = full_name.strip()

    if not seed:
        seed = "Planora User"

    encoded_seed = parse.quote(seed)

    return f"{DICEBEAR_INITIALS_BASE_URL}?seed={encoded_seed}"