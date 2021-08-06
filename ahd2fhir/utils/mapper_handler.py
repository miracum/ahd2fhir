from ahd2fhir.utils.custom_mappers import DeviceMapper, SmokingStatusMapper


class MapperHandler:
    def __init__(self, config):
        self.config = config
        self.mappers = [
            SmokingStatusMapper(self.config),
            DeviceMapper(None),
        ]

    def get_mappings(self, averbis_result, doc_ref):
        total_results = []
        for mapper in self.mappers:
            mapper_results = []
            print(mapper.ahd_type)
            for val in averbis_result:
                if val["type"] == mapper.ahd_type:
                    if results := mapper.get_resources(val, doc_ref) is not None:
                        mapper_results.append(results)

        return total_results

    def get_ahd_types(self):
        return [m.ahd_type for m in self.mappers]
