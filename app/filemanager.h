#ifndef FILEMANAGER_H
#define FILEMANAGER_H
#include <QObject>
class FileManager : public QObject
{
    Q_OBJECT
public:
    FileManager(QObject *parent = nullptr);
    void setOrthoDirectory(const QString &dirPath);
    QString getOrthoDirectory() const;
    bool hasOrthoDirectory() const;

    void setSpectralFiles(const QStringList &files);
    void addSpectralFiles(const QStringList &files);
    void clearSpectralFiles();
    QStringList getSpectralFiles() const;
    bool hasSpectralFiles() const;

    bool extractSpectralBands(QString &red, QString &nir, QString &rededge) const;
signals:
    void orthoDirectoryUpdated(const QString &dirPath);
    void spectralFilesUpdated(const QStringList &files);

private:
    QString m_orthoDirectory;
    QStringList m_spectralFiles;
};

#endif // FILEMANAGER_H
