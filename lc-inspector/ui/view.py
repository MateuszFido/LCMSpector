from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog

class View(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


    def on_browseLC(self):
        """
        Slot for the browseLC button. Opens a file dialog for selecting LC files,
        which are then added to the listLC widget and the model is updated.
        """
        lc_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select LC Files", "", "Text Files (*.txt);;All Files (*)")
        if lc_file_paths:
            self.listLC.clear()
            for lc_file_path in lc_file_paths:
                self.listLC.addItem(lc_file_path)  # Add each LC file path to the listLC widget
            self.update_lc_file_list()  # Update the model with the new LC files
            self.statusbar.showMessage(f"Files added, {len(lc_file_paths)} LC files loaded successfully.")

    def on_browseMS(self):
        """
        Slot for the browseMS button. Opens a file dialog for selecting MS files,
        which are then added to the listMS widget and the model is updated.
        """
        ms_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select MS Files", "", "MzML Files (*.mzML);;All Files (*)")
        if ms_file_paths:
            self.listMS.clear()
            for ms_file_path in ms_file_paths:
                self.listMS.addItem(ms_file_path)  # Add each MS file path to the listMS widget
            self.update_ms_file_list()  # Update the model with the new MS files
            self.statusbar.showMessage(f"Files added, {len(ms_file_paths)} MS files loaded successfully.")

    def on_browseAnnotations(self):
        """
        Slot for the browseAnnotations button. Opens a file dialog for selecting annotation files,
        which are then added to the listAnnotations widget and the model is updated.
        """
        annotation_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Annotation Files", "", "Text Files (*.txt);;All Files (*)")
        if annotation_file_paths:
            self.listAnnotations.clear()
            for annotation_file_path in annotation_file_paths:
                self.listAnnotations.addItem(annotation_file_path)  # Add each annotation file path to the listAnnotations widget
            self.update_annotation_file()  # Update the model with the new annotation files
            self.statusbar.showMessage(f"Files added, {len(annotation_file_paths)} annotation files loaded successfully.")

    def on_process(self):
        # Trigger the processing action in the controller
        """
        Slot for the process button. Triggers the processing action in the controller.
        """
        pass  # This is handled by the controller

    def update_lc_file_list(self):
        # Update the model with the LC file paths
        """
        Updates the model with the LC file paths currently in the listLC widget.

        Iterates over the listLC widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `lc_filelist` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listLC widget change,
        such as when new LC files are added or existing ones are removed.
        """
        lc_files = [self.listLC.item(i).text() for i in range(self.listLC.count())]
        self.controller.model.lc_measurements = lc_files  # Assuming you have a reference to the controller

    def update_ms_file_list(self):
        # Update the model with the MS file paths
        """
        Updates the model with the MS file paths currently in the listMS widget.

        Iterates over the listMS widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `ms_filelist` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listMS widget change,
        such as when new MS files are added or existing ones are removed.
        """
        ms_files = [self.listMS.item(i).text() for i in range(self.listMS.count())]
        self.controller.model.ms_measurements = ms_files  # Assuming you have a reference to the controller

    def update_annotation_file(self):
        # Update the model with the annotation file paths
        """
        Updates the model with the annotation file paths currently in the listAnnotations widget.

        Iterates over the listAnnotations widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `annotation_file` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listAnnotations widget change,
        such as when new annotation files are added or existing ones are removed.
        """
        annotation_files = [self.listAnnotations.item(i).text() for i in range(self.listAnnotations.count())]
        self.controller.model.annotations = annotation_files  # Store all annotation files

    def show_message(self, message):
        """
        Shows a message in the status bar.

        Parameters
        ----------
        message : str
            The message to show in the status bar.
        """
        self.statusbar.showMessage(message)

    def show_critical_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def setupUi(self, MainWindow):
        """
        Sets up the UI components for the main window.

        Parameters
        ----------
        MainWindow : QMainWindow
            The main window object for which the UI is being set up.
        
        This method configures the main window, central widget, tab widget, and various
        UI elements such as buttons, labels, combo boxes, and sliders. It applies size
        policies, sets geometries, and associates various UI elements with their respective
        actions. Additionally, it sets up the menu bar with file, edit, and help menus.
        """
        
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(851, 701)
        MainWindow.setToolTip("")
        MainWindow.setToolTipDuration(-1)
        MainWindow.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(850, 640))
        self.centralwidget.setObjectName("centralwidget")
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(0, 80, 851, 561))
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabWidget.setElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.setTabBarAutoHide(False)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.listLC = QtWidgets.QListWidget(parent=self.tab)
        self.listLC.setGeometry(QtCore.QRect(10, 70, 281, 411))
        self.listLC.setObjectName("listLC")
        self.label = QtWidgets.QLabel(parent=self.tab)
        self.label.setGeometry(QtCore.QRect(20, 40, 81, 16))
        self.label.setObjectName("label")
        self.comboBox = QtWidgets.QComboBox(parent=self.tab)
        self.comboBox.setGeometry(QtCore.QRect(10, 0, 241, 26))
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.browseLC = QtWidgets.QPushButton(parent=self.tab)
        self.browseLC.setGeometry(QtCore.QRect(180, 30, 113, 32))
        self.browseLC.setObjectName("browseLC")
        self.listMS = QtWidgets.QListWidget(parent=self.tab)
        self.listMS.setGeometry(QtCore.QRect(310, 70, 256, 331))
        self.listMS.setObjectName("listMS")
        self.label_2 = QtWidgets.QLabel(parent=self.tab)
        self.label_2.setGeometry(QtCore.QRect(320, 40, 101, 16))
        self.label_2.setObjectName("label_2")
        self.browseMS = QtWidgets.QPushButton(parent=self.tab)
        self.browseMS.setGeometry(QtCore.QRect(450, 30, 113, 32))
        self.browseMS.setObjectName("browseMS")
        self.listAnnotations = QtWidgets.QListWidget(parent=self.tab)
        self.listAnnotations.setGeometry(QtCore.QRect(580, 70, 256, 411))
        self.listAnnotations.setObjectName("listAnnotations")
        self.label_3 = QtWidgets.QLabel(parent=self.tab)
        self.label_3.setGeometry(QtCore.QRect(590, 10, 211, 16))
        self.label_3.setObjectName("label_3")
        self.processButton = QtWidgets.QPushButton(parent=self.tab)
        self.processButton.setGeometry(QtCore.QRect(380, 500, 113, 32))
        self.processButton.setObjectName("processButton")
        self.browseAnnotations = QtWidgets.QPushButton(parent=self.tab)
        self.browseAnnotations.setGeometry(QtCore.QRect(730, 30, 113, 32))
        self.browseAnnotations.setObjectName("browseAnnotations")
        self.layoutWidget = QtWidgets.QWidget(parent=self.tab)
        self.layoutWidget.setGeometry(QtCore.QRect(300, 430, 271, 56))
        self.layoutWidget.setObjectName("layoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.layoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtWidgets.QLabel(parent=self.layoutWidget)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.resolution = QtWidgets.QLabel(parent=self.layoutWidget)
        self.resolution.setObjectName("resolution")
        self.gridLayout.addWidget(self.resolution, 1, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.resSlider = QtWidgets.QSlider(parent=self.layoutWidget)
        self.resSlider.setSizeIncrement(QtCore.QSize(0, 0))
        self.resSlider.setMinimum(0)
        self.resSlider.setMaximum(5)
        self.resSlider.setSingleStep(1)
        self.resSlider.setPageStep(1)
        self.resSlider.setProperty("value", 4)
        self.resSlider.setSliderPosition(4)
        self.resSlider.setTracking(True)
        self.resSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.resSlider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
        self.resSlider.setTickInterval(1)
        self.resSlider.setObjectName("resSlider")
        self.gridLayout.addWidget(self.resSlider, 0, 1, 2, 1)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.comboBox_2 = QtWidgets.QComboBox(parent=self.tab_2)
        self.comboBox_2.setGeometry(QtCore.QRect(320, 30, 241, 26))
        self.comboBox_2.setObjectName("comboBox_2")
        self.label_5 = QtWidgets.QLabel(parent=self.tab_2)
        self.label_5.setEnabled(True)
        self.label_5.setGeometry(QtCore.QRect(239, 30, 72, 21))
        self.label_5.setObjectName("label_5")
        self.layoutWidget1 = QtWidgets.QWidget(parent=self.tab_2)
        self.layoutWidget1.setGeometry(QtCore.QRect(30, 70, 791, 441))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.layoutWidget1)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.graphicsView = QtWidgets.QGraphicsView(parent=self.layoutWidget1)
        self.graphicsView.setObjectName("graphicsView")
        self.gridLayout_2.addWidget(self.graphicsView, 0, 0, 1, 1)
        self.graphicsView_2 = QtWidgets.QGraphicsView(parent=self.layoutWidget1)
        self.graphicsView_2.setObjectName("graphicsView_2")
        self.gridLayout_2.addWidget(self.graphicsView_2, 0, 1, 1, 1)
        self.graphicsView_3 = QtWidgets.QGraphicsView(parent=self.layoutWidget1)
        self.graphicsView_3.setObjectName("graphicsView_3")
        self.gridLayout_2.addWidget(self.graphicsView_3, 1, 0, 1, 1)
        self.graphicsView_4 = QtWidgets.QGraphicsView(parent=self.layoutWidget1)
        self.graphicsView_4.setObjectName("graphicsView_4")
        self.gridLayout_2.addWidget(self.graphicsView_4, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tab_2, "")
        self.logo = QtWidgets.QLabel(parent=self.centralwidget)
        self.logo.setGeometry(QtCore.QRect(-10, 0, 871, 71))
        self.logo.setText("")
        self.logo.setPixmap(QtGui.QPixmap("logo.png"))
        self.logo.setScaledContents(True)
        self.logo.setObjectName("logo")
        self.logo.raise_()
        self.tabWidget.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.progressBar = QtWidgets.QProgressBar(parent=MainWindow)
        self.statusbar.addWidget(self.progressBar)
        self.progressBar.setVisible(False)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 851, 37))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(parent=self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuHelp = QtWidgets.QMenu(parent=self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.actionSave = QtGui.QAction(parent=MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionExit = QtGui.QAction(parent=MainWindow)
        self.actionExit.setObjectName("actionExit")
        self.actionPreferences = QtGui.QAction(parent=MainWindow)
        self.actionPreferences.setObjectName("actionPreferences")
        self.actionReadme = QtGui.QAction(parent=MainWindow)
        self.actionReadme.setObjectName("actionReadme")
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionExit)
        self.menuEdit.addAction(self.actionPreferences)
        self.menuHelp.addAction(self.actionReadme)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.label_5.setBuddy(self.label_5)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        self.resSlider.valueChanged['int'].connect(self.resolution.setNum) 
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        self.browseLC.clicked.connect(self.on_browseLC)
        self.browseMS.clicked.connect(self.on_browseMS)
        self.browseAnnotations.clicked.connect(self.on_browseAnnotations)
        self.processButton.clicked.connect(self.on_process)


    def retranslateUi(self, MainWindow):
        """
        Set the text of the UI elements according to the current locale.
        
        Arguments:
        ----------
            MainWindow: The main window object.
        """
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LC Inspector"))
        self.label.setText(_translate("MainWindow", "LC data (.txt)"))
        self.comboBox.setItemText(0, _translate("MainWindow", "Use MS-based annotations"))
        self.comboBox.setItemText(1, _translate("MainWindow", "Use pre-annotated chromatograms"))
        self.browseLC.setText(_translate("MainWindow", "Browse"))
        self.label_2.setText(_translate("MainWindow", "MS data (.mzml)"))
        self.browseMS.setText(_translate("MainWindow", "Browse"))
        self.label_3.setText(_translate("MainWindow", "(optional) LC annotation files (.txt)"))
        self.processButton.setText(_translate("MainWindow", "Process"))
        self.browseAnnotations.setText(_translate("MainWindow", "Browse"))
        self.label_4.setToolTip(_translate("MainWindow", "Set the resolution with which to interpolate a new m/z axis from the MS data. Default: 120,000"))
        self.label_4.setText(_translate("MainWindow", "Mass resolution"))
        self.resolution.setText(_translate("MainWindow", "120000"))
        self.resSlider.setToolTip(_translate("MainWindow", "Set the resolution with which to interpolate a new m/z axis from the MS data. Default: 120,000"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Upload"))
        self.label_5.setText(_translate("MainWindow", "Current file:"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Results"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionPreferences.setText(_translate("MainWindow", "Preferences"))
        self.actionReadme.setText(_translate("MainWindow", "Readme"))
