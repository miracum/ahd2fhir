from fhir.resources.R4B.resource import Resource

from ahd2fhir.utils.bundle_builder import BundleBuilder


def test_build_with_static_id_should_set_bundle_id_to_it():
    bundle_builder = BundleBuilder()

    bundle = bundle_builder.build_from_resources([Resource()], id="fixed")

    assert bundle.id == "fixed"


def test_build_without_given_id_should_generate_random_bundle_id():
    bundle_builder = BundleBuilder()

    bundle_a = bundle_builder.build_from_resources([Resource(), Resource()], None)
    bundle_b = bundle_builder.build_from_resources([], None)

    assert bundle_a.id != bundle_b.id
