#include "orthopresenter.h"
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QHttpMultiPart>
#include <QHttpPart>
#include <QJsonArray>
#include <QJsonObject>
#include <QListWidget>
#include <QMainWindow>
#include <QNetworkReply>
#include "ui_mainwindow.h"
#include <filemanager.h>
#include <filesystem>
#include <scriptmanager.h>
OrthoPresenter::OrthoPresenter(QObject* parent, Ui::MainWindow* ui)
    : QObject(parent)
    , ui(ui)
{
    m_fileManager = new FileManager();
    m_orthoScriptManager = new ScriptManager();
    m_networkManager = new QNetworkAccessManager(this);
    connect(m_orthoScriptManager,
            &ScriptManager::logMessage,
            ui->orthoOutputTextEdit,
            &QTextEdit::append);
    connect(m_orthoScriptManager, &ScriptManager::processStarted, this, [ui]() {
        ui->btnOrthoGen->setEnabled(false);
    });
    connect(m_orthoScriptManager, &ScriptManager::processFinished, this, [ui](bool) {
        ui->btnOrthoGen->setEnabled(true);
    });
    connect(ui->btnImportImgOrtho,
            &QPushButton::clicked,
            this,
            &OrthoPresenter::selectOrthoDirectory);
    connect(ui->btnOrthoGen, &QPushButton::clicked, this, &OrthoPresenter::generateOrthomosaic);
}
OrthoPresenter::~OrthoPresenter()
{
    delete m_fileManager;
    delete m_orthoScriptManager;
}
void OrthoPresenter::generateOrthomosaic()
{
    if (!m_fileManager->hasOrthoDirectory()) {
        ui->orthoOutputTextEdit->append("Aucune image sélectionnée.");
        return;
    }

    ui->btnOrthoGen->setEnabled(false);

    if (ui->radioLocal->isChecked()) {
        ui->orthoOutputTextEdit->append("--- Démarrage Orthomosaïque (DOCKER local) ---");

        QString absoluteImagesDir = m_fileManager->getOrthoDirectory();

        QString projectDir = QDir::currentPath() + "/results/ortho_local";
        QString imagesDestDir = projectDir + "/images";
        QString expectedOdmOutput = projectDir + "/odm_orthophoto/odm_orthophoto.tif";
        QString defaultPath = absoluteImagesDir + "_orthophoto.tif";
        QString finalDestPath = QFileDialog::getSaveFileName(ui->centralwidget,
                                                             "Enregistrer l'orthomosaïque",
                                                             defaultPath,
                                                             "Image TIFF (*.tif *.tiff)");
        if (finalDestPath.isEmpty()) {
            return;
        }

        try {
            if (std::filesystem::exists(imagesDestDir.toStdString())) {
                std::filesystem::remove_all(imagesDestDir.toStdString());
            }
            std::filesystem::create_directories(imagesDestDir.toStdString());

            ui->orthoOutputTextEdit->append(
                "Préparation de l'espace de travail (Copie des images)...");

            for (const auto& entry :
                 std::filesystem::directory_iterator(absoluteImagesDir.toStdString())) {
                if (entry.is_regular_file()) {
                    std::string ext = entry.path().extension().string();
                    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
                    if (ext == ".tif" || ext == ".tiff" || ext == ".jpg" || ext == ".jpeg") {
                        std::string destFile = imagesDestDir.toStdString() + "/"
                                               + entry.path().filename().string();
                        std::filesystem::copy(entry.path(),
                                              destFile,
                                              std::filesystem::copy_options::overwrite_existing);
                    }
                }
            }
            ui->orthoOutputTextEdit->append("Copie terminée.");

        } catch (const std::exception& e) {
            ui->orthoOutputTextEdit->append(QString("Erreur lors de la copie : %1").arg(e.what()));
            return;
        }

        QString program = "pkexec";
        QStringList args;

        QString featureQuality = ui->featureQualityComboBox->currentText();
        QString minNumFeatures = ui->minNumFeaturesLineEdit->text();
        if (minNumFeatures.isEmpty()) {
            minNumFeatures = "4000";
        }

        QString pcQuality = ui->pcQualityComboBox->currentText();
        QString matcherType = ui->matcherComboBox->currentText();
        QString sfmAlg = ui->sfmComboBox->currentText();

        args << "docker" << "run" << "--rm"
             << "-v" << projectDir + ":/datasets/code:z" << "opendronemap/odm"
             << "--project-path" << "/datasets"
             << "--primary-band" << "nir"
             << "--feature-quality" << featureQuality << "--min-num-features" << minNumFeatures
             << "--pc-quality" << pcQuality << "--matcher-type" << matcherType << "--sfm-algorithm"
             << sfmAlg << "--rerun-all";

        auto connection = std::make_shared<QMetaObject::Connection>();
        *connection = connect(
            m_orthoScriptManager,
            &ScriptManager::processFinished,
            this,
            [this, expectedOdmOutput, finalDestPath, connection](bool success) {
                QObject::disconnect(*connection);
                if (success) {
                    if (std::filesystem::exists(expectedOdmOutput.toStdString())) {
                        try {
                            std::filesystem::copy(expectedOdmOutput.toStdString(),
                                                  finalDestPath.toStdString(),
                                                  std::filesystem::copy_options::overwrite_existing);
                            ui->orthoOutputTextEdit->append("Orthomosaïque sauvegardée: :\n"
                                                            + finalDestPath);


                            QStringList bands = {"1", "2", "3", "4", "5"};
                            QStringList names = {"red3.TIF", "green2.TIF", "blue1.TIF", "NIR4.TIF", "rededge5.TIF"};

                            for (int i = 0; i < bands.size(); ++i) {
                                QProcess process;
                                QStringList args;
                                args << "-b" << bands[i]
                                     << finalDestPath
                                     << names[i];

                                process.start("gdal_translate", args);
                                process.waitForFinished(-1);

                                ui->orthoOutputTextEdit->append("Bande " + bands[i] + " exportée.");

                            }
                        } catch (const std::exception& e) {
                            ui->orthoOutputTextEdit->append(
                                QString("Erreur lors de l'export : %1").arg(e.what()));
                        }
                    } else {
                        ui->orthoOutputTextEdit->append("fichier odm_orthophoto.tif introuvable.");
                    }
                }
            }
            );

        m_orthoScriptManager->runCommand(program, args);
    }
}

void OrthoPresenter::selectOrthoDirectory()
{
    QString dir = QFileDialog::getExistingDirectory(ui->centralwidget,
                                                    "Sélectionner le dossier d'images",
                                                    QDir::homePath());
    if (!dir.isEmpty()) {
        m_fileManager->setOrthoDirectory(dir);
        ui->btnOrthoGen->setEnabled(true);
    }
}
