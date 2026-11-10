// SPDX-License-Identifier: GPL-3.0-only
#include <QCoreApplication>
#include <QPluginLoader>
#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QPluginLoader loader(QString::fromLocal8Bit(argv[1]));
    if (!loader.load() || !loader.instance()) {
        std::fprintf(stderr, "%s\n", qPrintable(loader.errorString()));
        return 1;
    }
    std::puts("Native clipboard factory loaded successfully");
    return 0;
}
