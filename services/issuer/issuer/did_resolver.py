import re
import httpx

# ACA-Py base class — imported at runtime when running inside ACA-Py.
# For standalone tests, we provide a minimal stub.
try:
    from aries_cloudagent.resolver.base import BaseDIDResolver, ResolverType
except ImportError:
    class ResolverType:
        NON_NATIVE = "non_native"
    class BaseDIDResolver:
        def __init__(self, type_=None):
            self.type = type_

SUPPORTED_DID_PATTERN = re.compile(r"^did:stratos:[a-zA-Z0-9._-]+$")

class StratosDIDResolver(BaseDIDResolver):
    """ACA-Py DID resolver plugin for the did:stratos method.

    Register in ACA-Py config:
        --plugin issuer.did_resolver
    ACA-Py will call setup() and then resolver.resolve(profile, did) as needed.
    """

    def __init__(self, api_url: str = "", api_key: str = ""):
        super().__init__(ResolverType.NON_NATIVE)
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.supported_did_regex = SUPPORTED_DID_PATTERN

    async def setup(self, context) -> None:
        """Called by ACA-Py on plugin load. Read config from context if needed."""
        settings = context.settings if hasattr(context, "settings") else {}
        self.api_url = settings.get("stratos.api_url", self.api_url)
        self.api_key = settings.get("stratos.api_key", self.api_key)

    async def resolve(self, profile, did: str) -> dict:
        """ACA-Py calls this for any did:stratos DID."""
        return await self._fetch_did_document(did)

    async def _fetch_did_document(self, did: str) -> dict:
        identifier = did.removeprefix("did:stratos:")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.api_url}/did/{identifier}",
                headers={"x-api-key": self.api_key},
            )
            r.raise_for_status()
            return r.json()
