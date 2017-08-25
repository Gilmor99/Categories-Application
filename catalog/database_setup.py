# Database Configuration file using SQLAlchemy
import os
import sys

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

### Table Class ####
Base = declarative_base()

### Each classe represent Table
### Each Column Represent field within the table

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

class Category(Base):
    ### Category Table #####
    __tablename__ = 'category'

    ### Columns ####
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, index=True)
    image = Column(String(250))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'image': self.image,
        }

class Items(Base):
    #### items Table #####
    __tablename__ = 'item'

    ### Columns ####
    name = Column(String(80), nullable=False, index=True)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    image = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
# We added this serialize function to be able to send JSON objects in a
# serializable format
    @property
    def serialize(self):

        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'image': self.image,
            }


########## Create the DB ################

engine = create_engine('sqlite:///categoriesitems.db')

Base.metadata.create_all(engine)
