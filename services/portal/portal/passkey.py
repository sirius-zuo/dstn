# services/portal/portal/passkey.py
import time
from webauthn import generate_registration_options, generate_authentication_options
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)
from webauthn.helpers import bytes_to_base64url

_CHALLENGE_TTL = 300  # 5 minutes
# dict: challenge_b64 → (business_number, expires_at)
# NOTE: in-process only — multi-worker deployments must replace this with a Redis-backed store.
_PENDING_CHALLENGES: dict[str, tuple[str, float]] = {}


class PasskeyManager:
    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def begin_registration(self, business_number: str, user_display_name: str) -> tuple[object, str]:
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=business_number.encode(),
            user_name=business_number,
            user_display_name=user_display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        challenge_b64 = bytes_to_base64url(options.challenge)
        _PENDING_CHALLENGES[challenge_b64] = (business_number, time.time() + _CHALLENGE_TTL)
        return options, challenge_b64

    def begin_authentication(self) -> tuple[object, str]:
        options = generate_authentication_options(
            rp_id=self.rp_id,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        challenge_b64 = bytes_to_base64url(options.challenge)
        _PENDING_CHALLENGES[challenge_b64] = ("", time.time() + _CHALLENGE_TTL)
        return options, challenge_b64

    def consume_challenge(self, challenge_b64: str) -> str | None:
        entry = _PENDING_CHALLENGES.pop(challenge_b64, None)
        if entry is None:
            return None
        business_number, expires_at = entry
        if time.time() > expires_at:
            return None
        return business_number

    def has_pending_challenge(self, challenge_b64: str) -> bool:
        entry = _PENDING_CHALLENGES.get(challenge_b64)
        if entry is None:
            return False
        _, expires_at = entry
        return time.time() <= expires_at
