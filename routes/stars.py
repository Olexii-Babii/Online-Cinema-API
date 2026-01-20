from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auxiliary_functions.movies import check_exists_star
from config.dependencies import get_current_user
from database import UserModel
from database.engine import get_db
from database.models.movies import StarModel, StarsMoviesModel
from schemas.movies import StarsResponseSchema, StarsRequestSchema

router = APIRouter()



@router.get("/", response_model=List[StarsResponseSchema])
async def get_stars(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    stars = await db.scalars(select(StarModel))

    if not stars:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stars found."
        )

    return stars.all()


@router.post("/", response_model=StarsResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_star(
        data: StarsRequestSchema,
        db: AsyncSession = Depends(get_db),
):
    db_star = await db.scalar(select(StarModel).where(StarModel.name == data.name))

    if db_star:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Star already exists.")

    new_star = StarModel(name=data.name)
    db.add(new_star)
    await db.commit()
    await db.refresh(new_star)

    return new_star


@router.patch("/{star_id}", response_model=StarsResponseSchema)
async def update_star(
        star_id: int,
        data: StarsRequestSchema,
        db: AsyncSession = Depends(get_db),
):
    db_star = await check_exists_star(star_id=star_id, db=db)

    star_with_same_name = await db.scalar(select(StarModel).where(
        StarModel.name == data.name,
        StarModel.id != star_id
    ))

    if star_with_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Star with this name ({data.name}) already exists."
        )

    db_star.name = data.name

    await db.commit()
    await db.refresh(db_star)

    return db_star


@router.delete("/{star_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
        star_id: int,
        db: AsyncSession = Depends(get_db),
):
    await check_exists_star(star_id=star_id, db=db)

    movies_count = await db.scalar(
        select(func.count())
        .select_from(StarsMoviesModel)
        .where(StarsMoviesModel.c.stars_id == star_id)
    )
    if movies_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There are already films with this star."
        )

    await db.execute(delete(StarModel).where(StarModel.id == star_id))
    await db.commit()

