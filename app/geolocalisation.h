#ifndef GEOLOCALISATION_H
#define GEOLOCALISATION_H

#include <QObject>
#include <filemanager.h>
#include <scriptmanager.h>
#include "mainwindow.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class Geolocalisation:public QWidget
{
    Q_OBJECT
public:
    Geolocalisation(QWidget* parent=nullptr,Ui::MainWindow *ui=nullptr);
public slots:
    void selectGeolocImg();
protected:
    bool eventFilter(QObject *obj, QEvent *event) override;
private:
    void pixel_to_gps(int x, int y);
    void compute_area();
    void displayGPS(float lon,float lat);
    Ui::MainWindow* ui;
    ScriptManager *m_scriptManager;
    FileManager *m_fileManager;
    QSize m_initialGeolocImgSize;
    QString current_image;
};

#endif // GEOLOCALISATION_H
