#ifndef TRAITEMENT_H
#define TRAITEMENT_H
#include <QString>

class Traitement
{
public:
    Traitement();
    QString band_detection;
    QString top_pct_detection;
    QString min_area_detection;
    QString top_pct_texture;
    QString min_area_texture;
    QString x_similarities;
    QString y_similarities;
    QString w_similarities;
    QString h_similarities;
    QString similarities_rectangle;
    QString radius_similarities;
    QString topk_similarities;
};

#endif // TRAITEMENT_H
