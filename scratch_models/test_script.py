from model_param import VirtualSource
from model_pydantic import VirtualSourceBasePyd

vs_d = VirtualSource(name="direct", converter_base="neutral")
vs_dicap = VirtualSource(
    name="diode+capacitor",
    V_input_drop_mV=300,
    C_intermediate_uF=10,
)

print(vs_dicap.harvester)
#print(dict(vs_dicap.params))
print(vs_dicap.params)
print(vs_dicap.param.harvester)

# also possible alternatives: traitlets, attrs
# note: only param and pydantic have an option to interface django
#       with djantic being more popular
# OR
#   pydantic -> jsonForms
#   django-jsonforms
# OR
# streamlit www.streamlit.io
# streamlit-pydantic    https://github.com/LukasMasuch/streamlit-pydantic
# streamlit-authenticator https://pypi.org/project/streamlit-authenticator/

pvs_d = VirtualSourceBasePyd(name="direct", converter_base="neutral")
pvs_dicap = VirtualSourceBasePyd(
    name="diode+capacitor",
    V_input_drop_mV=300,
    C_intermediate_uF=10,
)

print(pvs_dicap.harvester)
print(pvs_dicap.dict())

pvs_spec = VirtualSourceBasePyd(
    name="special",
    converter_base="BQ25570si",
    V_output_mV=3300,
)

print(pvs_spec.dict())
