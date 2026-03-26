#ifndef ORTHOPRESENTER_H
#define ORTHOPRESENTER_H
#include <QHttpMultiPart>
#include <QJsonDocument>
#include <QJsonObject>
#include <QListWidget>
#include <QMainWindow>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <filemanager.h>
#include <scriptmanager.h>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE
class OrthoPresenter : public QObject
{
    Q_OBJECT
public:
    OrthoPresenter(QObject *parent, Ui::MainWindow *ui);
    ~OrthoPresenter();
    void generateOrthomosaic();
    void selectOrthoDirectory();

private:
    ScriptManager *m_orthoScriptManager;
    FileManager *m_fileManager;
    Ui::MainWindow *ui;
    QNetworkAccessManager *m_networkManager;
};

#endif // ORTHOPRESENTER_H
