Categories List Application

The application allows the creation of categories with relevant items.

In order to run it, you will need to follow the following steps -

1. Set up a Vegrant VM environment with the attache vegrantfile.
2. The application using FlickrAPI to retrieve images from Flickr. Please
install FlickrAPI with $ pip install flickrapi  on the VM.
3. Run the database_setup.py application using the command $ python database_setup.py .
4. Run the application.py using the command $ python application.py .
5. From a web browser access the http://localhost:8000/categories address.
6. Once the application is running, you could review existing categories, or login
using a Google Account and add or edit categories and relevant items. Please note
that the security model of the application allows each user to view all existing categories
and items. However, it restricts changes or deletes to the owner of the category / item.
7. In addition, you can use JSON API to get list of categories or items from the application.
the JSON interface is as follow -
    a. Access all categories at - http://localhost:8000/categories/JSON
    b. Access the list of items of specific category at -  http://localhost:8000/categories/(category_id)/list/JSON
    c. Access specific item details at -  http://localhost:8000/categories/(category_id)/(item_id)/JSON


Enjoy the application !!!
