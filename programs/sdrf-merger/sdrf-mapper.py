import pandas as pd
import yaml
import sdrf_pipelines
from sdrf_pipelines.zooma.zooma import Zooma, SlimOlsClient
from sdrf_pipelines.openms.unimod import UnimodDatabase


with open(r'param2sdrf.yaml') as file:
   param_mapping = yaml.load(file, Loader=yaml.FullLoader)
   print(param_mapping["parameters"])

unimod = UnimodDatabase()

ptm = unimod.get_by_accession(10)
print(ptm)


