#include "filemanager.h"

FileManager::FileManager(QObject *parent)
    : QObject(parent)
{}
void FileManager::setOrthoDirectory(const QString &dirPath)
{
    if (m_orthoDirectory != dirPath) {
        m_orthoDirectory = dirPath;
        emit orthoDirectoryUpdated(m_orthoDirectory);
    }
}

QString FileManager::getOrthoDirectory() const
{
    return m_orthoDirectory;
}

bool FileManager::hasOrthoDirectory() const
{
    return !m_orthoDirectory.isEmpty();
}

void FileManager::setSpectralFiles(const QStringList &files)
{
    m_spectralFiles = files;
    emit spectralFilesUpdated(m_spectralFiles);
}

void FileManager::addSpectralFiles(const QStringList &files)
{
    m_spectralFiles.append(files);
    emit spectralFilesUpdated(m_spectralFiles);
}

void FileManager::clearSpectralFiles()
{
    m_spectralFiles.clear();
    emit spectralFilesUpdated(m_spectralFiles);
}

QStringList FileManager::getSpectralFiles() const
{
    return m_spectralFiles;
}

bool FileManager::hasSpectralFiles() const
{
    return !m_spectralFiles.isEmpty();
}

bool FileManager::extractSpectralBands(QString &red, QString &nir, QString &rededge) const
{
    red.clear();
    nir.clear();
    rededge.clear();

    for (const QString &file : m_spectralFiles) {
        if (file.endsWith("3.TIF", Qt::CaseInsensitive))
            red = file;
        else if (file.endsWith("4.TIF", Qt::CaseInsensitive))
            nir = file;
        else if (file.endsWith("5.TIF", Qt::CaseInsensitive))
            rededge = file;
    }

    return (!red.isEmpty() && !nir.isEmpty() && !rededge.isEmpty());
}
