import csv
import json
from dataclasses import dataclass
from bidict import bidict
from typing import Literal
from app import constant

class DataLoadError(Exception): pass
class FileMissingError(DataLoadError): pass
class DataFormatError(DataLoadError): pass
class InfoMissingError(DataLoadError): pass

"""
Files Description:
    - course_list.csv : Course Information (Course ID, Course Name, Credit Units)

    - equivalence_courses.csv : Equivalence Courses (Major, Course ID (CUHK), Course Name (CUHK), Course ID (CUHKSZ), Course Name (CUHKSZ))

    - course_list.json : Course list for each major (i.e. Faculty Package, Required Courses, Elective Courses, Research Component)

    - 2nd_major_credit_requirement.json : Second Major's Credit Requirement (Major, Credit Requirement)
"""

# --- Load Data ---
@dataclass(frozen = True) # Ensure data would keep unchanged
class CourseDataContext:
    course_info: dict[str, list[str]]
    equivalence_courses: dict[str, dict[str, str]]
    equivalence_bidicts: dict[str, bidict] 
    course_list: dict
    major_2_requirement: dict
    
def load_all_data() -> CourseDataContext:
    try:
        with open("data/course_list.csv", newline='', encoding = 'utf-8') as csvfile:
        # Course Information (Course ID, Course Name, Credit Units)
        
            reader = csv.DictReader(csvfile, 
                                    delimiter=',',
                                    fieldnames = ['code', 'title', 'units'])
            
            course_info: dict[str, list[str]] = {
                row['code']: [row['title'], row['units']] 
                for row in reader
            } 
        
        """
        Structure of course_info : 
            {
                code : [title, units]
            }
        """

        
    except FileNotFoundError as e:
        raise FileMissingError(f"course_list.csv Not Found: {e.filename}") from e
    
    except Exception as e: # for other cases
        raise DataFormatError(f"course_list.csv Parse Fail: {e}") from e

    try:
        with open("data/equivalence_courses.csv", newline='', encoding = 'utf-8') as csvfile:  
            # Equivalence Courses (Major, Course ID (CUHK), Course Name (CUHK), Course ID (CUHKSZ), Course Name (CUHKSZ))
            
            reader = csv.DictReader(csvfile, 
                                    delimiter=',',
                                    fieldnames = ['major', 'code(hk)', 'name(hk)', 'code(sz)', 'name(sz)'])
            
            equivalence_courses: dict[str, dict[str, str]] = {major: {} for major in constant.MAJOR_LIST}
            # Generate a empty dict object for each major
            
            """
            The structure of equivalence_courses: 
            {
                major : {
                    code(hk) : code(sz)
                }
            }
            """
            
            for row in reader:
                # Get the equivalence course ID
                equivalence_courses[row['major']][row['code(hk)']] = row['code(sz)']
                
                # Add equivalence course info to course_info
                if row['code(hk)'] not in course_info.keys():
                    unit = course_info[row['code(sz)']][1]
                    
                    course_info[row['code(hk)']] = [row['name(hk)'], unit]
                
                elif row['code(sz)'] not in course_info.keys():
                    unit = course_info[row['code(hk)']][1]

                    course_info[row['code(sz)']] = [row['name(sz)'], unit]

        equivalence_bidicts = {
            major: bidict(mapping) for major, mapping in equivalence_courses.items()
        }
        
    except FileNotFoundError as e:
        raise FileMissingError(f"equivalence_courses.csv Not Found: {e.filename}") from e

    except KeyError as e:
        raise DataFormatError(f"equivalence_courses.csv Parse Fail: {e}") from e
    
    except Exception as e:
        raise DataFormatError(f"equivalence_courses.csv Parse Fail: {e}") from e
        
    def _load_json(filepath : str):
        try:
            with open(filepath, "r") as jsonfile:
                return json.load(jsonfile)
            
        except FileNotFoundError as e:
            raise FileMissingError(f"{filepath} Not Found: {e.filename}") from e
        
        except json.JSONDecodeError as e:
            raise DataFormatError(f"{filepath} Wrong JSON Format: {e.msg}") from e 
        
        except Exception as e:
            raise DataFormatError(f"{filepath} Parse Fail: {e}") from e 
        
    course_list = _load_json("data/course_list.json")
    
    major_2_requirement = _load_json("data/2nd_major_credit_requirement.json")
    
    return CourseDataContext(
        course_info = course_info,
        equivalence_courses = equivalence_courses,
        equivalence_bidicts = equivalence_bidicts,
        course_list = course_list,
        major_2_requirement = major_2_requirement
    )
    
    """
    Explanation of similar variable names
    - course_list : Major's Required Courses, Electives etc.
    - course_info : Course_id : [Course_name, Credit]
    """
    
# --- Supplementary Functions ---
def determine_campus(course_id : str) -> Literal['hk', 'sz']:
    if len(course_id) >= 7:
        if course_id[3].isalpha():
            return 'hk'
        else:
            return 'sz'
    else:
        raise DataLoadError("Wrong Course ID")

    
def convert_course_id(context : CourseDataContext, major : str, course_id : str) -> str:
    try:
        data: bidict = context.equivalence_bidicts[major]
        if determine_campus(course_id) == "hk":
            return data[course_id]
        else:
            return data.inverse[course_id]
        
    except KeyError as e:
        raise InfoMissingError(f"{course_id} Not Found")
    
    except Exception as e:
            raise DataFormatError(f"Data Parse Fail: {e}") from e


# --- Data Retrieval Functions ---
def get_equivalence_courses(context : CourseDataContext, major : str = 'all') -> dict[str, dict[str, str]] | dict[str, str]:
    if major == 'all':
        return context.equivalence_courses
    
    else: 
        try:
            return context.equivalence_courses[major]
        
        except KeyError as e:
            raise InfoMissingError("Major Not Found") from e
        
        except Exception as e:
            raise DataFormatError(f"Data Parse Fail: {e}") from e
                 
   
def get_course_info(context : CourseDataContext, request : str = "all") -> dict[str, list[str]] | list[str]: 
    if request == "all":
        return context.course_info
    
    elif request == "id":
        return list(context.course_info.keys())
    
    else:
        try:
            return context.course_info[request]
        
        except KeyError as e:
            raise InfoMissingError(f"Course ID {request} Not Found")
        
        except Exception as e:
            raise DataFormatError(f"Data Parse Fail: {e}") from e
        
def get_course_list(context : CourseDataContext, major : str = "all") -> dict[str, str | list[str]]:
    if major == "all":
        return context.course_list
    
    else: 
        try:
            return context.course_list[major]
        
        except KeyError as e:
            raise InfoMissingError(f"{major} Not Found")

        except Exception as e:
            raise DataFormatError(f"Data Parse Fail: {e}") from e

def get_course_id_list(context : CourseDataContext) -> list[str]:
    return list(context.course_info.keys())


# def show_course_info(
#     context : CourseDataContext,
#     major : str, 
#     course_list : str | list[str], 
#     campus : Literal['hk', 'sz'], 
#     request_type : str = "courses"
# ) -> list[str | int]:
    
#     output_list : list[int | str] = []
    
#     if isinstance(course_list, str):
#         course_list = [course_list] # Convert to list object
        
#     for cid in course_list:
#         if request_type == "credits":
#             output_list.append(int(get_course_info(context, cid)[1]))
            
#         elif request_type == "courses":
#             if determine_campus(cid) != campus:
#                 try:
#                     cid = convert_course_id(context, major, cid)
                    
#                 except InfoMissingError:
#                     output_list.append("Unavailable")
#                     continue
            
#             output_list.append(f"{cid} | {get_course_info(context, cid)[0]}")
            
#         else:
#             raise InfoMissingError("Wrong value in parameter type")
                
#     return output_list
    
def get_major_2_requirement(context: CourseDataContext, major : str, category : str) -> int:
    return context.major_2_requirement[major][category]