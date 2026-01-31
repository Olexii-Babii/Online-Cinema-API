from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from auxiliary_functions.movies import check_exists_star, get_current_user
from database import UserModel
from database.engine import get_db
from database.models.movies import StarModel, StarsMoviesModel
from schemas.movies import StarsResponseSchema, StarsRequestSchema
from security.permissions import check_moder_or_admin

router = APIRouter()



@router.get("/",
            response_model=List[StarsResponseSchema],
            summary="Get list of stars.",
            description=(
                    "<h3>This endpoint allows users to get list of stars.</h3>"
            ),
            responses={
                404: {
                    "description": "No stars found.",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "No stars found."
                            }
                        }
                    },
                },
            },
            )
async def get_stars(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    stars = await db.scalars(select(StarModel))
    stars = stars.all()

    if not stars:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stars found."
        )

    return stars


@router.post("/",
             response_model=StarsResponseSchema,
             status_code=status.HTTP_201_CREATED,
             description=(
                     "<h3>This endpoint allows moderators or admins to create new star.</h3>"
             ),
             responses={
                 409: {
                     "description": "Star already exists.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Star already exists."
                             }
                         }
                     },
                 },
                 500: {
                     "description": "An error occurred while creating the star.",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "An error occurred while creating the star."
                             }
                         }
                     },
                 },
             },
             )
async def create_star(
        data: StarsRequestSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(check_moder_or_admin)
):
    db_star = await db.scalar(select(StarModel).where(StarModel.name == data.name))

    if db_star:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Star already exists.")

    try:
        new_star = StarModel(name=data.name)
        db.add(new_star)
        await db.commit()
        await db.refresh(new_star)

        return new_star

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the star."
        )

@router.patch("/{star_id}/",
              response_model=StarsResponseSchema,
              description=(
                      "<h3>This endpoint allows moderators or admins to update existing star.</h3>"
              ),
              responses={
                  404: {
                      "description": "Star with the given ID was not found.",
                      "content": {
                          "application/json": {
                              "example": {
                                  "detail": "Star with the given ID was not found."
                              }
                          }
                      },
                  },
                  409: {
                      "description": "Star with this name ({data.name}) already exists.",
                      "content": {
                          "application/json": {
                              "example": {
                                  "detail": "Star with this name ({data.name}) already exists."
                              }
                          }
                      },
                  },
                  500: {
                      "description": "An error occurred while updating the star.",
                      "content": {
                          "application/json": {
                              "example": {
                                  "detail": "An error occurred while updating the star."
                              }
                          }
                      },
                  },
              },
              )
async def update_star(
        star_id: int,
        data: StarsRequestSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(check_moder_or_admin)
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
    try:

        db_star.name = data.name

        await db.commit()
        await db.refresh(db_star)

        return db_star

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the star."
        )



@router.delete("/{star_id}/",
               status_code=status.HTTP_204_NO_CONTENT,
               description=(
                       "<h3>This endpoint allows moderators or admins to delete existing star."
                       "If there is movie with star in database, genre can't be deleted.</h3>"
               ),
               responses={
                   404: {
                       "description": "Star with the given ID was not found.",
                       "content": {
                           "application/json": {
                               "example": {
                                   "detail": "Star with the given ID was not found."
                               }
                           }
                       },
                   },
                   409: {
                       "description": "There are already films with this star.",
                       "content": {
                           "application/json": {
                               "example": {
                                   "detail": "There are already films with this star."
                               }
                           }
                       },
                   },
                   500: {
                       "description": "An error occurred while deleting the star.",
                       "content": {
                           "application/json": {
                               "example": {
                                   "detail": "An error occurred while deleting the star."
                               }
                           }
                       },
                   },
               },
               )
async def delete_star(
        star_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(check_moder_or_admin)
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

    try:
        await db.execute(delete(StarModel).where(StarModel.id == star_id))
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the star."
        )
