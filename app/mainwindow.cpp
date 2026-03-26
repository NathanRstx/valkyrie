#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QMessageBox>
#include <QFileDialog>
#include <QScrollArea>
#include <QPixmap>

#include <QDebug>

#include <QProcess>
#include <QFileInfo>

#include <QMouseEvent>

#include <QTextEdit>
#include <filesystem>
#include <iostream>
#include <orthopresenter.h>
#include "geolocalisation.h"
#define VERSION_NUMBER "0.1.2"
#define LAST_MODIFICATION_DATE "25/02/2026"
#define MEMBERS "Anas Barhdadi, Paul Ferrando-Tello, Elora Flahaut, Gireg Gambrelle, Baptiste Maillard, Nathan Restoux"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    m_orthoPresenter = new OrthoPresenter(this, ui);
    m_scriptManager = new ScriptManager(this);
    m_fileManager = new FileManager(this);
    connect(m_scriptManager,
            &ScriptManager::logMessage,
            ui->pythonOutputTextEdit,
            &QTextEdit::append);
    connect(m_scriptManager, &ScriptManager::processStarted, this, [this]() {
        ui->btnRun->setEnabled(false);
        ui->actionExecute->setEnabled(false);
    });
    connect(m_scriptManager, &ScriptManager::processFinished, this, [this](bool) {
        ui->btnRun->setEnabled(true);
        ui->actionExecute->setEnabled(true);
    });

    connect(ui->actionOpen, &QAction::triggered, this, &MainWindow::selectImages);
    connect(ui->actionExecute,&QAction::triggered,this,&MainWindow::executeProcess);
    connect(ui->actionAbout,&QAction::triggered,this,&MainWindow::onAboutAction);
    Geolocalisation* geolocator=new Geolocalisation(this,ui);
    ui->geolocImgLabel->installEventFilter(geolocator);
    connect(ui->geolocImportImgBtn, &QPushButton::clicked, geolocator, &Geolocalisation::selectGeolocImg);

    ui->centralwidget->setMouseTracking(true);

    for (auto child : ui->centralwidget->findChildren<QWidget*>()) {
        child->setMouseTracking(true);
    }
    setMouseTracking(true);
    connect(ui->action_OptionTraitement,&QAction::triggered,this,&MainWindow::TraitementOptions);
    _traitement = Traitement();
}

MainWindow::~MainWindow() { delete ui; }

void MainWindow::onAboutAction() {
    QMessageBox msgBox(this);
    QString text;
    text.append("Version ");
    text.append(VERSION_NUMBER);
    text.append(" (");
    text.append(LAST_MODIFICATION_DATE);
    text.append(")\n\n");
    text.append("Créé par : ");
    text.append(MEMBERS);
    msgBox.about(this,"A Propos",text);
}

void MainWindow::selectImages() {

    // Nettoyage des anciens dossiers
    try {
        if (std::filesystem::exists("images")) {
            std::filesystem::remove_all("images");
        }
        if (std::filesystem::exists("results")) {
            std::filesystem::remove_all("results");
        }

        std::filesystem::create_directory("images");
        std::filesystem::create_directory("results");

    } catch (const std::filesystem::filesystem_error& e) {
        std::cerr << "Filesystem error: " << e.what() << std::endl;
    }


    QStringList files = QFileDialog::getOpenFileNames(
        this,
        "Sélectionner images TIF",
        QDir::homePath(),
        "Images TIF (*.TIF *.tif)"
    );
    if (files.isEmpty()) { return; }

    m_fileManager->setSpectralFiles(files);
    ui->imgList->clear();
    ui->imgList->addItems(m_fileManager->getSpectralFiles());
    ui->btnRun->setEnabled(true);
    ui->actionExecute->setEnabled(true);
    ui->pythonOutputTextEdit->append("-> Fichiers sélectionnés. Prêt à lancer.");

    // Optimisation de vitesse : eviter toutes les conversions en .png si on importe beaucoup d'images
    if (ui->dontDisplayCheckBox->isChecked()) { return; }

    const int GRID_COLUMNS = 3;
    int idx = 0;
    for (const QString tifFile : m_fileManager->getSpectralFiles()) {
        QLabel* label = new QLabel();
        QFileInfo info(tifFile);
        QString pngFile = "images/" + info.completeBaseName() + ".png";
        QProcess::execute("convert", QStringList() << tifFile << pngFile);
        QPixmap pixmap(pngFile);
        if (!pixmap.isNull()) {
            label->setPixmap(pixmap.scaled(100, 100, Qt::KeepAspectRatio));
            label->show();
        } else {
            label->setText("Image not found");
        }
        ui->imgDisplayLayout->addWidget(label, idx / GRID_COLUMNS, idx % GRID_COLUMNS);
        idx++;
    }
}

void MainWindow::NDVE_NDRI(){
    if (!m_fileManager->hasSpectralFiles()) {
        ui->pythonOutputTextEdit->append("Aucun fichier sélectionné.");
        return;
    }

    QString redFile;
    QString nirFile;
    QString redEdgeFile;

    m_fileManager->extractSpectralBands(redFile, nirFile, redEdgeFile);

    if (redFile.isEmpty() || nirFile.isEmpty() || redEdgeFile.isEmpty()) {
        ui->pythonOutputTextEdit->append(
            "Erreur : fichiers 3.TIF, 4.TIF ou 5.TIF manquants.");
        return;
    }


    QString outputDir = "results/indices";
    try {
        std::filesystem::create_directory(outputDir.toStdString());
    } catch (...) {

    }

    QStringList arguments;
    arguments << "../../scripts/NdreNdvi.py"
              << "--red" << redFile
              << "--nir" << nirFile
              << "--rededge" << redEdgeFile
              << "--out" << outputDir;

    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}


//Pour les 3 méthodes, adapter les arguments avec un choix de l'utilisateur
void MainWindow::detection(){
    QString inputDir = "results/indices";
    QString outputDir = "results/detect_ndvi";
    if(_traitement.band_detection == "ndre"){
       outputDir = "results/detect_ndre";
    }


    try {
        std::filesystem::create_directories(outputDir.toStdString());
    } catch (...) {}

    QStringList arguments;
    arguments << "../../scripts/detection.py"
              << "--indir" << inputDir
              << "--band" << _traitement.band_detection
              << "--out" << outputDir
              << "--top_pct" <<_traitement.top_pct_detection
              << "--min_area" << _traitement.min_area_detection;

    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}

void MainWindow::detection_texture(){
    QString indexFile = "results/indices/NDRE.npy";
    QString outputDir = "results/detect_texture";

    try {
        std::filesystem::create_directories(outputDir.toStdString());
    } catch (...) {}

    QStringList arguments;
    arguments << "../../scripts/detection_textures.py"
              << "--index" << indexFile
              << "--out" << outputDir
              << "--top_pct" << _traitement.top_pct_texture
              << "--min_area" << _traitement.min_area_texture;

    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}

void MainWindow::similarities(){
    QString inputDir = "results/indices";

    ui->pythonOutputTextEdit->append("Lancement de similarities.py ...");

    QStringList arguments;
    if(_traitement.similarities_rectangle == "point")
    {
        arguments << "../../scripts/similarities.py"
                  << "--indir" << inputDir
                  << "--x" << _traitement.x_similarities
                  << "--y" << _traitement.y_similarities
                  << "--radius" << _traitement.radius_similarities
                  << "--topk" << _traitement.topk_similarities;
    }
    else{

        arguments << "../../scripts/similarities.py"
                  << "--indir" << inputDir
                  << "--x" << _traitement.x_similarities
                  << "--y" << _traitement.y_similarities
                  << "--w" << _traitement.w_similarities
                  << "--h" << _traitement.h_similarities
                  << "--radius" << _traitement.radius_similarities
                  << "--topk" << _traitement.topk_similarities;

    }



    m_scriptManager->runScript(arguments[0], arguments.mid(1));
}

void MainWindow::executeProcess()
{
    if (!m_fileManager->hasSpectralFiles()) {
        ui->pythonOutputTextEdit->append("Aucun fichier sélectionné.");
        return;
    }
    QString choice = ui->processPickerComboBox->currentText();
    ui->pythonOutputTextEdit->append("--- Démarrage : " + choice + " ---");
    if (!std::filesystem::exists("results/indices")) {
        ui->pythonOutputTextEdit->append("Les indices n'existent pas. Calcul NDVI/NDRE lancé.");
        NDVE_NDRI();
    }

    if (choice == "NDVI") {
        displayResultImage("results/indices/NDVI_preview.png");
    }
    if (choice == "NDRE") {
        displayResultImage("results/indices/NDRE_preview.png");
    }
    else if (choice == "Anomalies") {
        detection();
        if(_traitement.band_detection == "ndre"){
          displayResultImage("results/detect_ndre/candidates.png");
        }
        else{
            displayResultImage("results/detect_ndvi/candidates.png");
        }


    }
    else if (choice == "Textures") {
        detection_texture();
        displayResultImage("results/detect_texture/candidates.png");
    }
    else if (choice == "Similaritées") {
        similarities();
        displayResultImage("results/similarity/candidates.png");
    }

}

void MainWindow::displayResultImage(const QString& imagePath)
{
    if (!QFile::exists(imagePath)) {
        ui->pythonOutputTextEdit->append("Image introuvable : " + imagePath);
        return;
    }

    ImageWindow* imgWindow = new ImageWindow(imagePath);
    imgWindow->setAttribute(Qt::WA_DeleteOnClose);
    imgWindow->show();
}

void MainWindow::TraitementOptions()
{
    TraitementDialog dialog(_traitement, this);
    dialog.exec();
}
