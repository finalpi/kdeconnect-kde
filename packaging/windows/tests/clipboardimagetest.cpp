// SPDX-License-Identifier: GPL-3.0-only
#include "clipboardlistener.h"
#include "core/filetransferjob.h"
#include "core/networkpacket.h"
#include <QApplication>
#include <QClipboard>
#include <QFile>
#include <QImage>
#include <QMimeData>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>

class ClipboardImageTest : public QObject
{
    Q_OBJECT
    ClipboardListener *listener = ClipboardListener::instance();

    void prepare(FileTransferJob &job)
    {
        job.setProperty("clipboardImage", true);
        listener->prepareImageTransfer(&job);
    }
    bool writeImage(const QString &path)
    {
        QImage image(32, 18, QImage::Format_RGB32);
        image.fill(Qt::blue);
        return image.save(path, "PNG");
    }

private Q_SLOTS:
    void init()
    {
        listener->setText(QStringLiteral("test baseline"));
        QCoreApplication::processEvents();
    }
    void imageBecomesBitmapAndTransferFileIsRemoved()
    {
        QTemporaryDir dir;
        const auto path = dir.filePath(QStringLiteral("image.png"));
        QVERIFY(writeImage(path));
        NetworkPacket packet;
        FileTransferJob job(&packet, QUrl::fromLocalFile(path));
        prepare(job);
        QSignalSpy changed(listener, &ClipboardListener::clipboardChanged);
        listener->setFile(&job);
        QCoreApplication::processEvents();
        const auto *mime = QApplication::clipboard()->mimeData();
        QVERIFY(mime->hasImage());
        QVERIFY(!mime->hasUrls());
        QCOMPARE(qvariant_cast<QImage>(mime->imageData()).size(), QSize(32, 18));
        QVERIFY(!QFile::exists(path));
        QCOMPARE(changed.count(), 0); // An incoming image must not echo back to peers.
    }
    void newTextDuringTransferWins()
    {
        QTemporaryDir dir;
        const auto path = dir.filePath(QStringLiteral("image.png"));
        QVERIFY(writeImage(path));
        NetworkPacket packet;
        FileTransferJob job(&packet, QUrl::fromLocalFile(path));
        prepare(job);
        listener->setText(QStringLiteral("newer text"));
        listener->setFile(&job);
        QCOMPARE(QApplication::clipboard()->text(), QStringLiteral("newer text"));
        QVERIFY(!QFile::exists(path));
    }
    void latestImageRequestWins()
    {
        QTemporaryDir dir;
        const auto first = dir.filePath(QStringLiteral("first.png"));
        const auto second = dir.filePath(QStringLiteral("second.png"));
        QVERIFY(writeImage(first));
        QVERIFY(writeImage(second));
        NetworkPacket packet;
        FileTransferJob oldJob(&packet, QUrl::fromLocalFile(first));
        FileTransferJob newJob(&packet, QUrl::fromLocalFile(second));
        prepare(oldJob);
        prepare(newJob);
        listener->setFile(&oldJob);
        QCOMPARE(QApplication::clipboard()->text(), QStringLiteral("test baseline"));
        listener->setFile(&newJob);
        QVERIFY(QApplication::clipboard()->mimeData()->hasImage());
        QVERIFY(!QFile::exists(first));
        QVERIFY(!QFile::exists(second));
    }
    void invalidImageKeepsClipboard()
    {
        QTemporaryDir dir;
        const auto path = dir.filePath(QStringLiteral("bad.png"));
        QFile file(path);
        QVERIFY(file.open(QIODevice::WriteOnly));
        file.write("not an image");
        file.close();
        NetworkPacket packet;
        FileTransferJob job(&packet, QUrl::fromLocalFile(path));
        prepare(job);
        listener->setFile(&job);
        QCOMPARE(QApplication::clipboard()->text(), QStringLiteral("test baseline"));
        QVERIFY(!QFile::exists(path));
    }
    void oversizedImageKeepsClipboard()
    {
        QTemporaryDir dir;
        const auto path = dir.filePath(QStringLiteral("large.png"));
        QImage huge(10000, 10000, QImage::Format_Mono);
        huge.fill(0);
        QVERIFY(huge.save(path, "PNG"));
        NetworkPacket packet;
        FileTransferJob job(&packet, QUrl::fromLocalFile(path));
        prepare(job);
        listener->setFile(&job);
        QCOMPARE(QApplication::clipboard()->text(), QStringLiteral("test baseline"));
        QVERIFY(!QFile::exists(path));
    }
    void ordinaryFileKeepsUrlAndFile()
    {
        QTemporaryDir dir;
        const auto path = dir.filePath(QStringLiteral("ordinary.png"));
        QVERIFY(writeImage(path));
        NetworkPacket packet;
        FileTransferJob job(&packet, QUrl::fromLocalFile(path));
        listener->setFile(&job);
        QCOMPARE(QApplication::clipboard()->mimeData()->urls(), QList<QUrl>{QUrl::fromLocalFile(path)});
        QVERIFY(QFile::exists(path));
    }
};

QTEST_MAIN(ClipboardImageTest)
#include "clipboardimagetest.moc"
