#include "geolocalisation.h"
#include <QProcess>
#include <QFileDialog>
#include <QDebug>
#include "ui_mainwindow.h"
#include <QMouseEvent>
#include "scriptmanager.h"
Geolocalisation::Geolocalisation(QWidget* parent,Ui::MainWindow *_ui) : QWidget(parent)
{
   ui=_ui;
   m_scriptManager = new ScriptManager(this);
   connect(m_scriptManager,&ScriptManager::logMessage,this,[this] (const QString &message) {
        qDebug()<<message;
        if (message.contains(",")) {
                QStringList list = message.split(',');
                if (list.size() == 2) {
                    displayGPS(list[0].toFloat(), list[1].toFloat());
                }
        } });
}

void Geolocalisation::pixel_to_gps(int x, int y){
    QString iks=QString::number(x);
    QString igrec=QString::number(y);
    QStringList arguments;
    arguments << "../../scripts/geo_utils.py"
              << current_image
              << "../../DEM/dem_calvados.tif"
              << "pixel_to_gps"
              << iks
              << igrec;

    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}

void Geolocalisation::displayGPS(float lon,float lat){
    QString text;
    text.append("long:");
    text.append(QString::number(lon));
    text.append(", lat:");
    text.append(QString::number(lat));
    ui->GPScoordlabel->setText(text);
}
void Geolocalisation::compute_area(){

    QStringList arguments;
    arguments << "../../scripts/geo_utils.py"
              << ""
              << "../../DEM/dem_calvados.tif"
              << "compute_area"
              << "";

    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}

void Geolocalisation::selectGeolocImg() {
    QStringList files = QFileDialog::getOpenFileNames(
        this,
        "Sélectionner image TIF",
        QDir::homePath(),
        "Images TIF (*.TIF *.tif)"
    );
    if (files.isEmpty()) { return; }

    QFileInfo info(files[0]);
    QString pngFile = "images/" + info.completeBaseName() + ".png";
    current_image=files[0];
    QProcess::execute("convert", QStringList() << files[0] << pngFile);
    QPixmap pixmap(pngFile);
    if (!pixmap.isNull()) {
        m_initialGeolocImgSize = pixmap.size();
        ui->geolocImgLabel->setPixmap(pixmap.scaledToWidth(ui->geolocImgLabel->width()));
        ui->geolocImgLabel->show();
    } else {
        ui->geolocImgLabel->setText("Image not found");
    }
}

bool Geolocalisation::eventFilter(QObject *obj, QEvent *event)
{
    if (obj == ui->geolocImgLabel)
    {
        if (event->type() == QEvent::MouseMove || event->type() == QEvent::MouseButtonPress)
        {
            QMouseEvent *mouseEvent = static_cast<QMouseEvent*>(event);

            QPoint label_pos = mouseEvent->pos();
            QSize labelSize = ui->geolocImgLabel->size();

            QPoint real_image_relative_pos = label_pos;

            if (ui->geolocImgLabel->pixmap() != nullptr)
            {
                QSize pixmapSize = ui->geolocImgLabel->pixmap()->size();

                int x_offset = (labelSize.width() - pixmapSize.width()) / 2;
                int y_offset = (labelSize.height() - pixmapSize.height()) / 2;

                QPoint image_relative_pos = label_pos - QPoint(x_offset, y_offset);

                real_image_relative_pos = QPoint(
                    image_relative_pos.x() * m_initialGeolocImgSize.width() / pixmapSize.width(),
                    image_relative_pos.y() * m_initialGeolocImgSize.height() / pixmapSize.height()
                );

                if (real_image_relative_pos.x() < 0
                    || real_image_relative_pos.y() < 0
                    || real_image_relative_pos.x() > m_initialGeolocImgSize.width()
                    || real_image_relative_pos.y() > m_initialGeolocImgSize.height())
                {
                    return false;
                }
            }

            ui->mousePosLabel->setText(
                "x:" + QString::number(real_image_relative_pos.x()) +
                ", y:" + QString::number(real_image_relative_pos.y())
            );

            if (event->type() == QEvent::MouseButtonPress)
            {
                pixel_to_gps(real_image_relative_pos.x(), real_image_relative_pos.y());
            }
        }
    }

    return QObject::eventFilter(obj, event);
}
