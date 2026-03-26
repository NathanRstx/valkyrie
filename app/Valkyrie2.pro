QT       += core gui network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG += c++17

# You can make your code fail to compile if it uses deprecated APIs.
# In order to do so, uncomment the following line.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

SOURCES += \
    filemanager.cpp \
    geolocalisation.cpp \
    imagewindow.cpp \
    main.cpp \
    mainwindow.cpp \
    orthopresenter.cpp \
    scriptmanager.cpp \
    traitement.cpp \
    traitementdialog.cpp

HEADERS += \
    filemanager.h \
    geolocalisation.h \
    mainwindow.h \
    orthopresenter.h \
    scriptmanager.h \
    imagewindow.h \
    mainwindow.h \
    traitement.h \
    traitementdialog.h

FORMS += \
    mainwindow.ui

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target

DISTFILES +=
