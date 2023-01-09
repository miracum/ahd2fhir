import uuid
from typing import List

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.resource import Resource


class BundleBuilder:
    def build_from_resources(self, resources: List[Resource], id: str) -> Bundle:
        bundle_id = id
        if bundle_id is None:
            bundle_id = str(uuid.uuid4())

        bundle = Bundle(**{"id": bundle_id, "type": "transaction", "entry": []})

        for resource in resources:
            request = BundleEntryRequest(
                **{"url": f"{resource.resource_type}/{resource.id}", "method": "PUT"}
            )

            entry = BundleEntry.construct()
            entry.request = request
            entry.fullUrl = request.url
            entry.resource = resource

            bundle.entry.append(entry)

        return bundle
