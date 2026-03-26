#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QListWidget>
#include <QMainWindow>
#include "imagewindow.h"
#include <filemanager.h>
#include <orthopresenter.h>
#include <scriptmanager.h>
#include "traitement.h"
#include "traitementdialog.h"

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onAboutAction();

    void selectImages();
    void executeProcess();

    void NDVE_NDRI();

    void detection();

    void detection_texture();

    void similarities();

    void displayResultImage(const QString& folder);

    void TraitementOptions();

private:
    Ui::MainWindow *ui;
    ScriptManager *m_scriptManager;
    FileManager *m_fileManager;
    OrthoPresenter *m_orthoPresenter;
    QSize m_initialGeolocImgSize;
    Traitement _traitement;

};
#endif // MAINWINDOW_H
