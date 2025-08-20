import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.teachers_model import Teacher
from app.models.timetable_slot_model import TimetableSlot
from app.models.model import Base

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from loguru import logger


router = APIRouter(prefix="/api/system", tags=["system"])
# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.delete("/reset_data")
async def reset_data(db: Session = Depends(get_db)):
    try:
        meta = Base.metadata
        for table in reversed(meta.sorted_tables):
            if table.name != "users":
                db.execute(table.delete())
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Đã xóa toàn bộ dữ liệu ngoại trừ bảng users."}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Xóa dữ liệu thất bại: " + str(e))
    
@router.post("/import_data")
async def import_data(
    classes_information: UploadFile = File(...),
    subjects_information: UploadFile = File(...),
    teachers_information: UploadFile = File(...),
    timetable_slots_information: UploadFile = File(...),
    db: Session = Depends(get_db)
    ):
    logger.error("----- START IMPORT DATA -------")

    if import_timetable_slot(db, timetable_slots_information) and\
          import_subjects(db, subjects_information) and\
             import_classes(db, classes_information) and\
                 import_teachers(db, teachers_information):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Import thành công."}
        )
    else:
        raise HTTPException(status_code=500, detail="Import không thành công. Kiểm tra lại dữ liệu trong file excel, reset dữ liệu trong CSDL và thực hiện import lại từ đầu.")

def import_timetable_slot(db, timetable_slots_file):
    timetable_slots_file = timetable_slots_file.file.read()
    df_timetble_slots = pd.read_excel(io.BytesIO(timetable_slots_file))
    # Lặp và ghi vào DB
    for idx, row in df_timetble_slots.iterrows():
        try:
            # Đọc theo chỉ số cột: 0 = Cột A, 1 = Cột B, 2 = Cột C
            day_of_week = row[0]
            session = row[1]
            period = int(row[2])
            if not day_of_week or not session or not period:
                logger.debug(f"[IMPORT_TIMETABLE] Bỏ qua dòng {idx+1} do thiếu thông tin.")
                continue
            existing = db.query(TimetableSlot).filter(
                TimetableSlot.day_of_week == day_of_week,
                TimetableSlot.session == session,
                TimetableSlot.period == period
            ).first()
            if existing:
                logger.debug(f"[IMPORT_TIMETABLE] Bỏ qua dòng {idx+1} do đã tồn tại trong CSDL.")
                continue

            slot = TimetableSlot(
                day_of_week=day_of_week,
                session=session,
                period=int(period)
            )
            db.add(slot)
        except Exception as e:
            logger.error(f"[IMPORT_TIMETABLE] Dòng {idx+1}: {str(e)}")
            return False
    db.commit()
    logger.info('[IMPORT_TIMETABLE] Import timetable successfully.')
    return True

def import_subjects(db, subjects_file):
    # Đọc dữ liệu từ file Excel
    subjects_file = subjects_file.file.read()
    df_subjects = pd.read_excel(io.BytesIO(subjects_file))

    # Ghi từng dòng vào DB (nếu chưa tồn tại)
    try:
        for idx, row in df_subjects.iterrows():
            name = str(row[0]).strip() if pd.notna(row[0]) else None
            code = str(row[1]).strip() if pd.notna(row[1]) else None
            lesson_per_week = int(row[2]) if pd.notna(row[2]) else None
            subject_group = str(row[3]).strip() if pd.notna(row[3]) else None
            required = str(row[4]).strip() == "Có" if pd.notna(
                row[4]) else False
            exam_required = str(row[5]).strip(
            ) == "Có" if pd.notna(row[5]) else False
            description = str(row[6]).strip() if len(
                row) > 6 and pd.notna(row[6]) else None
            status = str(row[7]).strip() if len(
                row) > 7 and pd.notna(row[7]) else "active"

            if not name or not code or not lesson_per_week:
                logger.debug(f"[IMPORT_SUBJECTS] Bỏ qua dòng {idx+1} do thiếu thông tin mã môn, tên môn hoặc số tiết/tuần.")
                continue
                # raise ValueError("Thiếu tên hoặc mã môn học")

            existing = db.query(Subject).filter(Subject.code == code).first()
            if existing:
                logger.debug(f"[IMPORT_SUBJECTS] Bỏ qua dòng {idx+1} do đã tồn tại trong CSDL.")
                continue

            subject_obj = Subject(
                name=name,
                code=code,
                required=required,
                lesson_per_week=lesson_per_week,
                subject_group=subject_group,
                exam_required=exam_required,
                description=description,
                status=status
            )
            db.add(subject_obj)

    except Exception as e:
        logger.error(f"[IMPORT_SUBJECTS] Dòng {idx+1} ({row[0]}): {str(e)}")
        return False
    db.commit()
    logger.info(f'[IMPORT_SUBJECTS] Import subjects successfully.')
    return True
    
def import_classes(db, classes_file):
    try:
        # === Đọc Excel ===
        classes_file = classes_file.file.read()
        df_classes = pd.read_excel(io.BytesIO(classes_file))

        # === Import từng lớp ===
        for idx, row in df_classes.iterrows():
            name = str(row[0]).strip()

            # Bỏ qua nếu đã tồn tại
            if db.query(Class).filter_by(name=name).first():
                logger.debug(f"[IMPORT_CLASSES] Bỏ qua dòng {idx+1} do đã tồn tại trong CSDL.")
                continue

            grade = int(row[1])
            student_count = int(row[2])
            subject_codes = str(row[3]).split(",") if pd.notna(row[3]) else []
            subjects = db.query(Subject).filter(Subject.code.in_(subject_codes)).all()

            if not name or not subjects:
                logger.debug(f"[IMPORT_CLASSES] Bỏ qua dòng {idx+1} do thiếu thông tin tên lớp hoặc mã môn học.")
                continue

            clazz = Class(
                name=name,
                grade=grade,
                student_count=student_count,
                subjects=subjects
            )
            db.add(clazz)
    except Exception as e:
        logger.error(f"[IMPORT_CLASSES] Dòng {idx+1} ({row[0]}): {str(e)}")
        return False

    db.commit()
    logger.info(f'[IMPORT_CLASSES] Import classes successfully.')
    return True

def import_teachers(db, teachers_file):
    try:
        # Đọc file Excel
        teachers_file = teachers_file.file.read()
        df_teachers = pd.read_excel(io.BytesIO(teachers_file))
        # Lặp từng dòng để tạo Teacher
        for idx, row in df_teachers.iterrows():
            code=row[0],
            name=row[1],
            max_weekly_lessons=int(row[2])
            if db.query(Teacher).filter_by(code=code).first():
                logger.debug(f"[IMPORT_TEACHERS] Bỏ qua dòng {idx+1} do đã tồn tại trong CSDL.")
                continue  # bỏ qua nếu đã tồn tại
            
            subject_codes = str(row[3]).split(",")
            subjects = db.query(Subject).filter(Subject.code.in_(subject_codes)).all()
            
            if not code or not name or not subjects or not max_weekly_lessons:
                logger.debug(f"[IMPORT_TEACHERS] Bỏ qua dòng {idx+1} do thiếu thông tin mã giáo viên, tên giáo viên, môn dạy hoặc số tiết/tuần.")
                continue

            # Gán slot bận
            unavailable_slots = []
            slot_labels = str(row[4]).split(",") if pd.notna(row[4]) else []
            for label in slot_labels:
                slot = get_slot_by_label(db, label.strip())
                if slot:
                    unavailable_slots.append(slot)

            new_teacher = Teacher(
                code=code,
                name=name,
                max_weekly_lessons=max_weekly_lessons,
                # available_morning=bool(row["available_morning"]),
                # available_afternoon=bool(row["available_afternoon"]),
                # status="active",
                subjects=subjects,
                unavailable_slots=unavailable_slots
            )
            db.add(new_teacher)
    except Exception as e:
        logger.error(f"[IMPORT_TEACHERS] Dòng {idx+1} ({row[0]}): {str(e)}")
        return False

    db.commit()
    return True


# Tạo mapping để tra nhanh
def get_slot_by_label(db, label: str):
    try:
        d, sess, per = label.split("-")
        return db.query(TimetableSlot).filter_by(
            day_of_week=d, session=sess, period=int(per)
        ).first()
    except:
        return None
        