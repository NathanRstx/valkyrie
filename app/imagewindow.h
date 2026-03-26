#ifndef IMAGEWINDOW_H
#define IMAGEWINDOW_H

#include <QWidget>
#include <QLabel>
#include <QScrollArea>
#include <QVBoxLayout>
#include <QPixmap>

class ImageWindow : public QWidget
{
    Q_OBJECT

public:
    explicit ImageWindow(const QString& imagePath, QWidget *parent = nullptr);

private:
    QLabel *imageLabel;
    QScrollArea *scrollArea;
};

#endif // IMAGEWINDOW_H
