# Valkyrie
Logiciel réalisé dans le cadre des projets 2A de l'ENSICAEN

Barhdadi Anas  
Ferrando-tello Paul 
Flahaut Elora
Gambrelle Gireg
Maillard Baptiste
Restoux Nathan


## Getting started

### Prérequis
Logiciel réalisé avec Qt5

Pour l'utilisation des scripts, il est nécessaire d'avoir installé sur sa machine : python3, puis les librairies rasterio,cv2, pillow, exifread.

A noter que pillow et exifread ne sont nécessaires que pour la géolocalisation.

Pour l'utilisation d'OpenDroneMap , il faut installer docker et gdal pour décomposer le geotiff obtenu.


Sous linux Ubuntu:

pour les scripts d'analyse:

installation de python3 et pip

sudo apt install -y python3 python3-pip python3-dev

modules python :

sudo apt install -y gdal-bin libgdal-dev libgl1 libglib2.0-0

sudo pip3 install opencv-python rasterio exifread pillow

gdal:

sudo apt install gdal-bin libgdal-dev


docker :

sudo apt install docker-cli   
ou
sudo apt install podman-docker


### Utilisation du logiciel:
Lancer l'application  Valkyrie située dans le dosier app/Release/application ou alors si vous modifiez le code c++ Compiler via QT en chargeant Valkyrie2.pro et configurer dans le dossier app/build/Desktop-Debug, puis ctrl+R dans l'application pour lancer le logiciel.

Orthomosaïque :
en cliquant sur le bouton "importer images" de l'onglet orthomosaïque, Chargez le dossier contenant toutes les images capturées par drone puis cliquez sur "générer orthomosaïque" et choisir un dossier pour mettre le résultat.
Si tout se passe bien, on obtient une orthomosaïque des images principales ainsi que 5 mosaïques correspondant aux différentes bandes dans le dossier choisi.
Essayez avec plus de points(exemple 8000) pour que le programme aboutisse.
Mettre des performances pas trop hautes pour un traitement qui ne dure pas 3h(littéralement).
De plus OpenDroneMap ne fonctionnera pas si il ya très peu d'images.

Traitements : 
-Importer les images que l'on souhaite étudier en cliquant sur "importer images", les noms des images doivent finir en 1.TIF pour le red, 4.TIF pour le NIR et 5.TIF pour le rededge.

-Les résultats des traitements sont stockés dans le dossier résultats du dossier app/build/Desktop-Debug/results

-Les options permettent de choisir l'indice utilisé pour la detection ndve ou ndri; le pourcentage  et la taille minimum des zones anormales conservées par la detection;

-le pourcentage  et la taille minimum des zones anormales en texture conservées; 

On peut aussi choisir de regarder les zones similaires par rapport à un point ou par rapport à une zone, dans le cas d'un point, il s'agit des paramètres x,y dans le cas d'un rectangle, le point x,y correspond au sommet en haut à gauche du rectange et w et h ses dimensions.

-les paramètres topk et Radius permettent de choisir le pourcentage  et la taille minimum des zones similaires

Attention, il y a un bug pas encore corrigé, l'application tente d'afficher le résultat du traitement alors que le script est encore en cours d'éxecution, relancer le traitement une deuxième fois permet de visualiser.

Géolocalisation:

chargez image.tif

cliquer sur un poxel affiche les coordonnées en bas à gauche
