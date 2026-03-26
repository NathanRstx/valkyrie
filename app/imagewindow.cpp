#include "imagewindow.h"
#include <QMessageBox>

ImageWindow::ImageWindow(const QString& imagePath, QWidget *parent)
    : QWidget(parent)
{
    setWindowTitle(imagePath);
    resize(800, 600);

    QPixmap pixmap(imagePath);

    if (pixmap.isNull()) {
        QMessageBox::warning(this, "Erreur", "Impossible de charger l'image.");
        return;
    }

    imageLabel = new QLabel;
    imageLabel->setPixmap(pixmap);
    imageLabel->setAlignment(Qt::AlignCenter);

    scrollArea = new QScrollArea;
    scrollArea->setWidget(imageLabel);
    scrollArea->setWidgetResizable(true);

    QVBoxLayout *layout = new QVBoxLayout;
    layout->addWidget(scrollArea);

    setLayout(layout);
}
