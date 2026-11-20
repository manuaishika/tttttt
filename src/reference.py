"""Reference data: Indian states/UTs, cities and a seed institution registry.

Why hand-curated and in code: these lists are small, stable and need to be reviewable in
a diff. Everything here is public, well-known geography; coordinates for institutions are
approximate campus locations (good for a map marker, not for surveying) and are labelled
as such in the docs.
"""
from __future__ import annotations
from dataclasses import dataclass, field

STATE, UT = "State", "Union Territory"


@dataclass(frozen=True)
class Region:
    name: str                 # canonical name used everywhere in the dataset
    code: str                 # ISO 3166-2:IN suffix
    kind: str                 # State | Union Territory
    capital: str
    lat: float                # approximate centroid-ish point, used only as map fallback
    lon: float
    aliases: tuple[str, ...] = field(default_factory=tuple)  # free-text-safe aliases
    codes: tuple[str, ...] = field(default_factory=tuple)    # abbreviations: exact-match only


# NOTE on `codes`: abbreviations such as AP, MP, UP, TN are only accepted when the whole
# field *is* the abbreviation (structured input). They are NEVER matched inside free text
# because "MP" (Member of Parliament), "AP" (Associated Press), "AI"/"UP" etc. would
# create false positives.
REGIONS: list[Region] = [
    # ---- 28 states ----
    Region("Andhra Pradesh", "AP", STATE, "Amaravati", 15.9, 79.7, ("Andhra",), ("AP", "AND")),
    Region("Arunachal Pradesh", "AR", STATE, "Itanagar", 28.2, 94.7, (), ("AR", "ARP")),
    Region("Assam", "AS", STATE, "Dispur", 26.2, 92.9, (), ("AS", "ASM")),
    Region("Bihar", "BR", STATE, "Patna", 25.1, 85.3, (), ("BR", "BH")),
    Region("Chhattisgarh", "CG", STATE, "Raipur", 21.3, 81.9, ("Chattisgarh",), ("CG", "CT", "CHH")),
    Region("Goa", "GA", STATE, "Panaji", 15.3, 74.0, (), ("GA",)),
    Region("Gujarat", "GJ", STATE, "Gandhinagar", 22.7, 71.6, (), ("GJ", "GUJ")),
    Region("Haryana", "HR", STATE, "Chandigarh", 29.1, 76.1, (), ("HR", "HY")),
    Region("Himachal Pradesh", "HP", STATE, "Shimla", 31.9, 77.2, ("Himachal",), ("HP",)),
    Region("Jharkhand", "JH", STATE, "Ranchi", 23.6, 85.3, (), ("JH", "JHK")),
    Region("Karnataka", "KA", STATE, "Bengaluru", 15.3, 75.7, (), ("KA", "KAR")),
    Region("Kerala", "KL", STATE, "Thiruvananthapuram", 10.5, 76.3, ("Keralam",), ("KL", "KER")),
    Region("Madhya Pradesh", "MP", STATE, "Bhopal", 23.5, 78.6, (), ("MP",)),
    Region("Maharashtra", "MH", STATE, "Mumbai", 19.7, 75.7, (), ("MH", "MAH")),
    Region("Manipur", "MN", STATE, "Imphal", 24.7, 93.9, (), ("MN", "MNP")),
    Region("Meghalaya", "ML", STATE, "Shillong", 25.5, 91.4, (), ("ML", "MEG")),
    Region("Mizoram", "MZ", STATE, "Aizawl", 23.2, 92.8, (), ("MZ", "MIZ")),
    Region("Nagaland", "NL", STATE, "Kohima", 26.1, 94.6, (), ("NL", "NAG")),
    Region("Odisha", "OD", STATE, "Bhubaneswar", 20.5, 84.4, ("Orissa",), ("OD", "OR", "ORI")),
    Region("Punjab", "PB", STATE, "Chandigarh", 31.0, 75.4, (), ("PB", "PUN")),
    Region("Rajasthan", "RJ", STATE, "Jaipur", 26.6, 73.9, (), ("RJ", "RAJ")),
    Region("Sikkim", "SK", STATE, "Gangtok", 27.6, 88.5, (), ("SK", "SIK")),
    Region("Tamil Nadu", "TN", STATE, "Chennai", 11.1, 78.7, ("Tamilnadu",), ("TN", "TAM")),
    Region("Telangana", "TS", STATE, "Hyderabad", 17.9, 79.0, (), ("TS", "TG", "TEL")),
    Region("Tripura", "TR", STATE, "Agartala", 23.8, 91.7, (), ("TR", "TRI")),
    Region("Uttar Pradesh", "UP", STATE, "Lucknow", 27.0, 80.9, (), ("UP",)),
    Region("Uttarakhand", "UK", STATE, "Dehradun", 30.1, 79.2, ("Uttaranchal",), ("UK", "UT", "UA", "UTT")),
    Region("West Bengal", "WB", STATE, "Kolkata", 23.0, 87.9, ("Bengal",), ("WB",)),
    # ---- 8 union territories (kept separate, per the project brief) ----
    Region("Andaman and Nicobar Islands", "AN", UT, "Port Blair", 11.7, 92.7,
           ("Andaman and Nicobar", "Andaman & Nicobar", "A&N Islands"), ("AN",)),
    Region("Chandigarh", "CH", UT, "Chandigarh", 30.7, 76.8, (), ("CH", "CHD")),
    Region("Dadra and Nagar Haveli and Daman and Diu", "DH", UT, "Daman", 20.4, 72.9,
           ("Dadra and Nagar Haveli", "Daman and Diu", "Daman & Diu"), ("DH", "DD", "DN")),
    Region("Delhi", "DL", UT, "New Delhi", 28.6, 77.1,
           ("NCT of Delhi", "National Capital Territory of Delhi"), ("DL", "NCT")),
    Region("Jammu and Kashmir", "JK", UT, "Srinagar/Jammu", 33.8, 76.6,
           ("Jammu & Kashmir", "J&K"), ("JK",)),
    Region("Ladakh", "LA", UT, "Leh", 34.2, 77.6, (), ("LA", "LDK")),
    Region("Lakshadweep", "LD", UT, "Kavaratti", 10.6, 72.6, (), ("LD",)),
    Region("Puducherry", "PY", UT, "Puducherry", 11.9, 79.8, ("Pondicherry",), ("PY", "PDY")),
]

REGION_BY_NAME = {r.name: r for r in REGIONS}
STATES_ONLY = [r for r in REGIONS if r.kind == STATE]
UTS_ONLY = [r for r in REGIONS if r.kind == UT]
assert len(STATES_ONLY) == 28 and len(UTS_ONLY) == 8

# ---- Cities → state. A city mention is secondary evidence for the state. ----
CITY_TO_STATE: dict[str, str] = {}
for _state, _cities in {
    "Karnataka": ["Bengaluru", "Bangalore", "Mysuru", "Mysore", "Mangaluru", "Hubballi", "Belagavi"],
    "Telangana": ["Hyderabad", "Warangal", "Secunderabad"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy"],
    "Kerala": ["Thiruvananthapuram", "Trivandrum", "Kochi", "Cochin", "Kozhikode", "Technopark"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Navi Mumbai", "Thane"],
    "Gujarat": ["Ahmedabad", "Gandhinagar", "Surat", "Vadodara", "GIFT City", "Rajkot"],
    "Uttar Pradesh": ["Lucknow", "Noida", "Greater Noida", "Kanpur", "Varanasi", "Prayagraj", "Ghaziabad"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
    "West Bengal": ["Kolkata", "Siliguri", "Kharagpur"],
    "Bihar": ["Patna"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela"],
    "Assam": ["Guwahati", "Dispur"],
    "Andhra Pradesh": ["Visakhapatnam", "Vizag", "Amaravati", "Vijayawada", "Tirupati", "Guntur"],
    "Haryana": ["Gurugram", "Gurgaon", "Faridabad", "Panipat", "Sonipat"],
    "Punjab": ["Ludhiana", "Mohali", "Amritsar", "Jalandhar", "Patiala"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad"],
    "Chhattisgarh": ["Raipur", "Bilaspur", "Bhilai"],
    "Himachal Pradesh": ["Shimla", "Dharamshala"],
    "Goa": ["Panaji", "Margao"],
    "Manipur": ["Imphal"], "Meghalaya": ["Shillong"], "Mizoram": ["Aizawl"],
    "Nagaland": ["Kohima", "Dimapur"], "Sikkim": ["Gangtok"],
    "Arunachal Pradesh": ["Itanagar"], "Tripura": ["Agartala"],
    "Jammu and Kashmir": ["Srinagar"], "Ladakh": ["Leh"],
    "Puducherry": ["Puducherry"], "Chandigarh": ["Chandigarh"],
}.items():
    for _c in _cities:
        CITY_TO_STATE[_c] = _state

# Cities whose coordinates we trust for a map marker (approximate city centres).
CITY_COORDS: dict[str, tuple[float, float]] = {
    "Bengaluru": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867), "Chennai": (13.0827, 80.2707),
    "Mumbai": (19.0760, 72.8777), "Pune": (18.5204, 73.8567), "Kolkata": (22.5726, 88.3639),
    "Ahmedabad": (23.0225, 72.5714), "Gandhinagar": (23.2156, 72.6369), "Lucknow": (26.8467, 80.9462),
    "Thiruvananthapuram": (8.5241, 76.9366), "Kochi": (9.9312, 76.2673), "Bhubaneswar": (20.2961, 85.8245),
    "Jaipur": (26.9124, 75.7873), "Visakhapatnam": (17.6868, 83.2185), "Amaravati": (16.5730, 80.3580),
    "Guwahati": (26.1445, 91.7362), "Bhopal": (23.2599, 77.4126), "Indore": (22.7196, 75.8577),
    "Patna": (25.5941, 85.1376), "Noida": (28.5355, 77.3910), "Gurugram": (28.4595, 77.0266),
    "Chandigarh": (30.7333, 76.7794), "Dehradun": (30.3165, 78.0322), "Ranchi": (23.3441, 85.3096),
    "Raipur": (21.2514, 81.6296), "Coimbatore": (11.0168, 76.9558), "Delhi": (28.6139, 77.2090),
}
CITY_ALIAS = {"Bangalore": "Bengaluru", "Trivandrum": "Thiruvananthapuram", "Cochin": "Kochi",
              "Vizag": "Visakhapatnam", "Gurgaon": "Gurugram"}


# ---- Seed institution registry ------------------------------------------
@dataclass(frozen=True)
class Institution:
    name: str
    kind: str                 # academic | government | research_org
    city: str
    state: str
    lat: float                # approximate campus location
    lon: float
    aliases: tuple[str, ...] = ()


INSTITUTIONS: list[Institution] = [
    Institution("IIT Madras", "academic", "Chennai", "Tamil Nadu", 12.9916, 80.2336, ("IITM", "Indian Institute of Technology Madras")),
    Institution("IIT Bombay", "academic", "Mumbai", "Maharashtra", 19.1334, 72.9133, ("IITB", "Indian Institute of Technology Bombay")),
    Institution("IIT Delhi", "academic", "New Delhi", "Delhi", 28.5450, 77.1926, ("IITD", "Indian Institute of Technology Delhi")),
    Institution("IIT Kanpur", "academic", "Kanpur", "Uttar Pradesh", 26.5123, 80.2329, ("IITK", "Indian Institute of Technology Kanpur")),
    Institution("IIT Kharagpur", "academic", "Kharagpur", "West Bengal", 22.3149, 87.3105, ("IIT KGP", "Indian Institute of Technology Kharagpur")),
    Institution("IIT Hyderabad", "academic", "Sangareddy", "Telangana", 17.5948, 78.1239, ("IITH", "Indian Institute of Technology Hyderabad")),
    Institution("IIT Guwahati", "academic", "Guwahati", "Assam", 26.1878, 91.6911, ("IITG", "Indian Institute of Technology Guwahati")),
    Institution("IIT Roorkee", "academic", "Roorkee", "Uttarakhand", 29.8649, 77.8966, ("IITR", "Indian Institute of Technology Roorkee")),
    Institution("IIT Gandhinagar", "academic", "Gandhinagar", "Gujarat", 23.2113, 72.6849, ("IITGN", "Indian Institute of Technology Gandhinagar")),
    Institution("IIT Ropar", "academic", "Rupnagar", "Punjab", 30.9677, 76.4737, ("Indian Institute of Technology Ropar",)),
    Institution("IIT Jodhpur", "academic", "Jodhpur", "Rajasthan", 26.4725, 73.1131, ("Indian Institute of Technology Jodhpur",)),
    Institution("IIT Patna", "academic", "Patna", "Bihar", 25.5357, 84.8517, ("Indian Institute of Technology Patna",)),
    Institution("IIT Bhubaneswar", "academic", "Bhubaneswar", "Odisha", 20.1486, 85.6706, ("Indian Institute of Technology Bhubaneswar",)),
    Institution("IIT Indore", "academic", "Indore", "Madhya Pradesh", 22.5200, 75.9200, ("Indian Institute of Technology Indore",)),
    Institution("IIT Mandi", "academic", "Mandi", "Himachal Pradesh", 31.7826, 76.9961, ("Indian Institute of Technology Mandi",)),
    Institution("IIT Tirupati", "academic", "Tirupati", "Andhra Pradesh", 13.6906, 79.5917, ("Indian Institute of Technology Tirupati",)),
    Institution("IIT Palakkad", "academic", "Palakkad", "Kerala", 10.7261, 76.6841, ("Indian Institute of Technology Palakkad",)),
    Institution("IIT Dharwad", "academic", "Dharwad", "Karnataka", 15.4985, 74.9859, ("Indian Institute of Technology Dharwad",)),
    Institution("IIT Goa", "academic", "Farmagudi", "Goa", 15.4251, 73.9795, ("Indian Institute of Technology Goa",)),
    Institution("IIT (BHU) Varanasi", "academic", "Varanasi", "Uttar Pradesh", 25.2677, 82.9913, ("IIT BHU", "IIT Varanasi")),
    Institution("IIT (ISM) Dhanbad", "academic", "Dhanbad", "Jharkhand", 23.8143, 86.4413, ("IIT ISM", "IIT Dhanbad")),
    Institution("IISc Bengaluru", "academic", "Bengaluru", "Karnataka", 13.0219, 77.5671, ("IISc", "Indian Institute of Science", "IISc Bangalore")),
    Institution("IISER Pune", "academic", "Pune", "Maharashtra", 18.5413, 73.8305, ("Indian Institute of Science Education and Research Pune",)),
    Institution("IISER Kolkata", "academic", "Mohanpur", "West Bengal", 22.9650, 88.5233, ("Indian Institute of Science Education and Research Kolkata",)),
    Institution("IISER Mohali", "academic", "Mohali", "Punjab", 30.6656, 76.7285, ("Indian Institute of Science Education and Research Mohali",)),
    Institution("IISER Bhopal", "academic", "Bhopal", "Madhya Pradesh", 23.2870, 77.2740, ("Indian Institute of Science Education and Research Bhopal",)),
    Institution("IISER Thiruvananthapuram", "academic", "Thiruvananthapuram", "Kerala", 8.6784, 77.1380, ("IISER TVM",)),
    Institution("IIIT Hyderabad", "academic", "Hyderabad", "Telangana", 17.4455, 78.3489, ("IIIT-H", "International Institute of Information Technology Hyderabad")),
    Institution("IIIT Delhi", "academic", "New Delhi", "Delhi", 28.5459, 77.2732, ("IIIT-D", "Indraprastha Institute of Information Technology")),
    Institution("IIIT Bangalore", "academic", "Bengaluru", "Karnataka", 12.8447, 77.6632, ("IIITB",)),
    Institution("Indian Statistical Institute Kolkata", "academic", "Kolkata", "West Bengal", 22.6490, 88.3770, ("ISI Kolkata",)),
    Institution("TIFR Mumbai", "research_org", "Mumbai", "Maharashtra", 18.9086, 72.8138, ("Tata Institute of Fundamental Research", "TIFR")),
    Institution("Anna University", "academic", "Chennai", "Tamil Nadu", 13.0108, 80.2357),
    Institution("University of Hyderabad", "academic", "Hyderabad", "Telangana", 17.4600, 78.3300, ("UoH",)),
    Institution("Jadavpur University", "academic", "Kolkata", "West Bengal", 22.4967, 88.3714),
    Institution("Savitribai Phule Pune University", "academic", "Pune", "Maharashtra", 18.5525, 73.8247, ("SPPU",)),
    Institution("Digital University Kerala", "academic", "Thiruvananthapuram", "Kerala", 8.5586, 76.8810, ("IIITM-K", "IIITMK", "IIITM Kerala")),
    Institution("BITS Pilani", "academic", "Pilani", "Rajasthan", 28.3637, 75.5870, ("Birla Institute of Technology and Science",)),
    Institution("IIM Ahmedabad", "academic", "Ahmedabad", "Gujarat", 23.0314, 72.5398, ("IIMA", "Indian Institute of Management Ahmedabad")),
    Institution("AIIMS Delhi", "academic", "New Delhi", "Delhi", 28.5672, 77.2100, ("All India Institute of Medical Sciences Delhi",)),
    Institution("NIMHANS", "academic", "Bengaluru", "Karnataka", 12.9429, 77.5964, ("National Institute of Mental Health and Neurosciences",)),
    Institution("PGIMER Chandigarh", "academic", "Chandigarh", "Chandigarh", 30.7646, 76.7761, ("PGIMER",)),
    Institution("C-DAC Pune", "research_org", "Pune", "Maharashtra", 18.5393, 73.8250, ("CDAC Pune", "C-DAC")),
    Institution("Wadhwani AI", "research_org", "Mumbai", "Maharashtra", 19.0760, 72.8777, ("Wadhwani Institute for Artificial Intelligence",)),
    Institution("Telangana AI Mission (T-AIM)", "government", "Hyderabad", "Telangana", 17.3850, 78.4867, ("T-AIM", "TAIM", "Telangana AI Mission")),
    Institution("Karnataka Digital Economy Mission (KDEM)", "government", "Bengaluru", "Karnataka", 12.9716, 77.5946, ("KDEM",)),
    Institution("Kerala Startup Mission", "government", "Thiruvananthapuram", "Kerala", 8.5586, 76.8810, ("KSUM",)),
]
INSTITUTION_BY_NAME = {i.name: i for i in INSTITUTIONS}
