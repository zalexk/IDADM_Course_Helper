MAJOR_LIST : tuple[str, ...] = (
    "University Core",
    "Interdisciplinary Data Analytics",
    "Information Engineering",
    "Integrated BBA", 
    "Systems Engineering and Engineering Management",
    "Mathematics",
    "Statistics (CUHK)",
    "Financial Engineering",
    "Marketing and Communication",
    "Computer Science and Engineering",
    "Electrical and Computer Engineering",
    "Mathematics and Applied Mathematics",
    "Statistics (CUHK(SZ))"
)

MAJOR_2nd_list = MAJOR_LIST[2:] 

# Faculty whose English language requirement applies, per 2nd major.
# Financial Engineering may fulfil ANY of the three faculties' requirements,
# so its catalogue is the merge of all three lists.
ENGLISH_FACULTY : dict[str, tuple[str, ...]] = {
    "Information Engineering": ("Engineering",),
    "Integrated BBA": ("Business",),
    "Systems Engineering and Engineering Management": ("Engineering",),
    "Mathematics": ("Science",),
    "Statistics (CUHK)": ("Science",),
    "Financial Engineering": ("Business", "Engineering", "Science"),
    "Marketing and Communication": ("Business",),
    "Computer Science and Engineering": ("Engineering",),
    "Electrical and Computer Engineering": ("Engineering",),
    "Mathematics and Applied Mathematics": ("Science",),
    "Statistics (CUHK(SZ))": ("Science",),
}

FACULTY_NAMES : dict[str, str] = {
    "Business": "Faculty of Business Administration",
    "Engineering": "Faculty of Engineering",
    "Science": "Faculty of Science",
}

STUDY_CAMPUS = {
    "Year 1 Sem 1": "CUHK",
    "Year 1 Sem 2": "CUHKSZ",
    "Year 1 Summer (CUHK)": "CUHK",
    "Year 1 Summer (CUHKSZ)": "CUHKSZ",
    "Year 2 Sem 1": "CUHKSZ",
    "Year 2 Sem 2": "CUHK",
    "Year 2 Summer (CUHK)": "CUHK",
    "Year 2 Summer (CUHKSZ)": "CUHKSZ",
    "Year 3 Sem 1": "CUHK",
    "Year 3 Sem 2": "CUHKSZ",
    "Year 3 Summer (CUHK)": "CUHK",
    "Year 3 Summer (CUHKSZ)": "CUHKSZ",
    "Year 4 Sem 1": "CUHKSZ",
    "Year 4 Sem 2": "CUHK"
}

GRADUATION_REQUIREMENT : dict = {
    "University Core": {
        "Chinese Language": 5,
        "English Language": 8,
        "GE: Foundation Courses": 6,
        "GE: Four Areas (Area A, C, D)": 7,
        "College GE": 6,
        "Understanding China": 1,
        "Hong Kong in the Wider Constitutional Order": 1,
        "Digital Literacy and Computational Thinking": 3,
        "Physical Education": 2,
    },
    "1st Major": {
        "Faculty Package": 9,
        "Required Courses": 18,
        "COOP": 3,
        "Elective": 27,
        "Elective Group A": 6,
        "Elective Group B": 12,
        "Elective (3000+)": 12,
        "Elective (4000)": 6,
    },
    "Research Component": 3,
    "Total Credit": 129,
}

