import pandas as pd
import re
import yaml
import sdrf_pipelines
import os.path
from sdrf_pipelines.zooma.zooma import Zooma, OlsClient
from sdrf_pipelines.openms.unimod import UnimodDatabase
from sdrf_pipelines.sdrf.sdrf import SdrfDataFrame

## Accessing ontologies and CVs
unimod = UnimodDatabase()
olsclient = OlsClient()
#print(ols_out)

# modifications have the same column name, not working with pandas
# therefore separated
mod_columns = pd.DataFrame()

## For summary at the end
overwritten = set()

with open(r'param2sdrf.yml') as file:
   param_mapping = yaml.load(file, Loader=yaml.FullLoader)
   mapping = param_mapping["parameters"]


## READ PARAMETERS FOR RUNNING WORKFLOW
with open(r'test_params.yml') as file:
   tparams_in = yaml.load(file, Loader=yaml.FullLoader)
   params_in = tparams_in["params"]
   rawfiles = tparams_in["rawfiles"]
   fastafile = tparams_in["fastafile"]



## DO WE HAVE A SDRF FILE?
sdrf_content = pd.DataFrame()
has_sdrf = os.path.isfile("./sdrf.tsv")
if has_sdrf :
   sdrf_content = pd.read_csv("sdrf.tsv", sep="\t")
   mod_columns = sdrf_content.filter(like="comment[modification parameters]")
   sdrf_content = sdrf_content.drop(columns=mod_columns.columns)
   # delete columns with fixed/variable modification info
   if "fixed_mods" in params_in.keys():
      ttt = [x for x in mod_columns.columns if any(mod_columns[x].str.contains("MT=fixed")) ]
      mod_columns.drop(ttt, axis=1, inplace=True)
      overwritten.add("fixed_mods")
   if "variable_mods" in params_in.keys():
      ttt = [x for x in mod_columns.columns if any(mod_columns[x].str.contains("MT=variable")) ]
      mod_columns.drop(ttt, axis=1, inplace=True)
      overwritten.add("variable_mods")
   
   ## Check for raw files and update URIs
   # TODO

else:
   ## write sdrf with raw files, also use experimental design
   ## TODO
   print()
   
## FIRST STANDARD PARAMETERS
# FOR GIVEN PARAMETERS
# CHECK WHETHER COLUMN IN SDRF TO PUT WARNING AND OVERWRITE
# IF NOT GIVEN, WRITE COLUMN
for p in mapping:
   pname = p["name"]
   ptype = p["type"]
   print("---- Parameter: " + pname + ": ----")
   if(pname in list(params_in.keys())) :
      print("Found in parameter file")
      pvalue = params_in[pname]
   else:
      print("Setting to default: " + p["default"])
      pvalue = p["default"]

   psdrf = "comment[" + p["sdrf"] + "]"



   if (psdrf) in sdrf_content.keys() :
      if (len(set(sdrf_content[psdrf])) > 1) :
         exit("ERROR: multiple values for parameter " + pname + " in sdrf file\n We recommend separating the file into parts with the same data analysis parameters")
      print("WARNING: Overwriting values in sdrf file with " + pvalue)
      overwritten.add(pname)

   # for each type: check consistency
   #print(type(pvalue))
   if ptype == "boolean" :
       if not isinstance(pvalue, bool) :
         exit("ERROR: " + pname + " needs to be either \"true\" or \"false\"!!")
   if ptype == "str" :
       if not isinstance(pvalue, str) :
         exit("ERROR: " + pname + " needs to be a string!!")
   if ptype == "integer" : 
       if not isinstance(pvalue, int) :
         exit("ERROR: " + pname + " needs to be a string!!")
   if ptype == "float" : 
       if not isinstance(pvalue, (float, int)) :
         exit("ERROR: " + pname + " needs to be a numeric value!!")
   if ptype == "class" :
      not_matching = [x for x in pvalue.split(",") if x not in p["value"]]
      if not_matching != [] :
         exit("ERROR: " + pname + " needs to have one of these values: " + ' '.join(p["value"]) + "!!\n" + ' '.join(not_matching) + " did not match")
         
      
   # Mass tolerances: do they include Da or ppm exclusively?
   if pname == "fragment_mass_tolerance" or pname == "precursor_mass_tolerance" :
      unit = pvalue.split(" ")[1] 
      if unit != "Da" and unit != "ppm" :
        exit("ERROR: " + pname + " allows only units of \"Da\" and \"ppm\", separated by space from the value!!\nWe found " + unit)

   ## ENZYME AND MODIFICATIONS: LOOK UP ONTOLOGY VALUES
   if pname == "enzyme" :
    ols_out = olsclient.search(pvalue, ontology="MS", exact=True)
    if ols_out == None or len(ols_out) > 1 :
       exit("ERROR: enzyme " + pvalue + " not found in the MS ontology, see https://bioportal.bioontology.org/ontologies/MS/?p=classes&conceptid=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FMS_1001045 for available terms")
    pvalue = "NT=" + pvalue + ";AC=" + ols_out[0]["short_form"]

       
   ## Modifications: look up in Unimod
   if pname == "fixed_mods" or pname == "variable_mods" :
      mods = pvalue.split(",")
      for m in mods :
         tmod = m.split(" of ")
         if len(tmod) < 2:
            exit("ERROR: Something wrong with the modification entry " + m + ". It should be PSI_MS_NAME of RESIDUE. Note that it should be single residues")
         modname = tmod[0]
         modpos = tmod[1]
         found = [x for x in unimod.modifications if modname == x.get_name()]
         if found == [] :
            exit("ERROR: " + m + " not found in Unimod. Check the \"PSI-MS Names\" in unimod.org. Also check whether you used space between the comma separated modifications")
         modtype = "fixed"
         if (pname == "variable_mods") : modtype = "variable"            
         if re.match("[A-Z]",modpos) :
            mod_columns[len(mod_columns.columns)+1] = "NT=" + modname + ";AC=" + found[0].get_accession() + ";MT=" + modtype + ";TA=" + modpos
         elif modpos in ["Protein N-term", "Protein C-term", "Any N-term", "Any C-term"] :
            mod_columns[len(mod_columns.columns)+1] = "NT=" + modname + ";AC=" + found[0].get_accession() + ";MT=" + modtype + ";PP=" + modpos
         else :
            exit("ERROR: Wrong residue given: " + modpos + ". Should be either one upper case letter or any of \"Protein N-term\", \"Protein C-term\", \"Any N-term\", \"Any C-term\"")


#print(found_list[0].get_name())


   ## Now finally writing the value
   else : 
     sdrf_content[psdrf] = pvalue
         

   

## OVERWRITE RAW FILES IF GIVEN TO DIRECT TO THE CORRECT LOCATION?

## ADD FASTA FILE TO SDRF (COMMENT:FASTA DATABASE FILE)?

## WRITE EXPERIMENTAL DESIGN IF NO SDRF?


## adding modification columns
colnames = list(sdrf_content.columns)  + ["comment[modification parameters]"] * len(mod_columns.columns)

sdrf_content = pd.concat([sdrf_content, mod_columns], axis=1)

print("--- Writing sdrf file into sdrf_local.tsv ---")
sdrf_content.to_csv("sdrf_local.tsv", sep="\t", header=colnames, index=False) 

## TODO: verify with sdrf-parser
check_sdrf = SdrfDataFrame()
check_sdrf.parse("sdrf_local.tsv")
check_sdrf.validate("mass_spectrometry")


print("########## SUMMARY #########")
print("--- The following parameters have been overwritten in the sdrf file: ---")
for p in overwritten :
   print(p)
