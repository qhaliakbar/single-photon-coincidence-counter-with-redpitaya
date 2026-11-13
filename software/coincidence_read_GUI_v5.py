"""
Red Pitaya Coincidence Counter - control GUI

PyQt5 application that controls a Red Pitaya STEMlab 125-14 over SSH to
count events on two detector channels and the coincidences between them.

  LOAD FPGA IMAGE  uploads the coincidence bitstream (../bitstream) and
                   programs the FPGA with fpgautil.
  START            runs coincidence_read_v2.py on the board, which streams
                   singles A, singles B and coincidence rates (Hz).
  STOP             ends the run.
  COPY DATA        downloads the CSV file from the board.

Requires: PyQt5, pyqtgraph, paramiko, scp
"""



import os
import sys
import time
import paramiko
from scp import SCPClient
import scp

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import pyqtgraph as pg

from PyQt5.QtWidgets import QApplication

# Defaults shown in the GUI. Change them in the window, or edit here.
DEFAULT_IP = "169.254.101.10"   # your board's IP, or its name: rp-XXXXXX.local
DEFAULT_USER = "root"           # Red Pitaya factory default
DEFAULT_PASSWORD = "root"       # factory default; never commit a real password



# ============================================================
# SSH acquisition worker
# ============================================================

class SSHWorker(QThread):

    data_signal = pyqtSignal(float,float,float,float)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()


    def __init__(self, ip, user, password, duration, filename):

        super().__init__()

        self.ip = ip
        self.user = user
        self.password = password
        self.duration = duration
        self.filename = filename

        self.running = True
        self.first_data = True
        self.ssh = None



    def run(self):

        try:

            self.ssh = paramiko.SSHClient()

            self.ssh.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )


            self.status_signal.emit("Connecting...")

            self.ssh.connect(
                hostname=self.ip,
                username=self.user,
                password=self.password,
                timeout=5
            )


            self.status_signal.emit("Connected")


            command = (
                f"python3 coincidence_read_v2.py "
                f"--time {self.duration} "
                f"--file /root/{self.filename}"
            )


            stdin, stdout, stderr = self.ssh.exec_command(
                command,
                bufsize=1
            )


            stdout.channel.set_combine_stderr(True)


            while self.running:


                line = stdout.readline()


                if not line:
                    break


                line=line.strip()


                if not line[0].isdigit():
                    continue



                try:

                    values=line.split(",")


                    if len(values)!=4:
                        continue


                    t=float(values[0])
                    coin=float(values[1])
                    a=float(values[2])
                    b=float(values[3])


                    if self.first_data:
                        self.first_data=False
                        continue


                    self.data_signal.emit(
                        t,
                        coin,
                        a,
                        b
                    )


                except Exception as e:

                    self.status_signal.emit(
                        f"Parse error {e}"
                    )



            if self.ssh:
                self.ssh.close()
            
            self.finished_signal.emit()
            
            self.quit()



        except Exception as e:

            self.status_signal.emit(
                "SSH ERROR: "+str(e)
            )



    def stop(self):

        self.running=False

        try:

            if self.ssh:

                self.ssh.exec_command(
                    "pkill -f coincidence_read_v2.py"
                )

        except:
            pass




# ============================================================
# FPGA Image Loader Worker
# ============================================================
class FPGAWorker(QThread):

    status_signal = pyqtSignal(str)

    def __init__(self, ip, user, password):

        super().__init__()

        self.ip = ip
        self.user = user
        self.password = password

        self.local_bitstream = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
            "..", "bitstream", "red_pitaya_top.bit.bin"))


    def run(self):
    
        try:
    
            self.status_signal.emit("Connecting to Red Pitaya...")
    
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
            ssh.connect(
                hostname=self.ip,
                username=self.user,
                password=self.password,
                timeout=5
            )
    
            #
            # Upload coincidence bitstream
            #
    
            self.status_signal.emit("Uploading coincidence bitstream...")
    
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(
                    self.local_bitstream,
                    "/root/red_pitaya_top.bit.bin"
                )
    
            self.status_signal.emit("Upload complete.")
    
            #
            # Program FPGA
            #
    
            self.status_signal.emit("Programming FPGA...")
    
            stdin, stdout, stderr = ssh.exec_command(
                "/opt/redpitaya/bin/fpgautil -b /root/red_pitaya_top.bit.bin"
            )
    
            output = stdout.read().decode()
            error = stderr.read().decode()
    
            if error.strip():
                self.status_signal.emit(error)
            else:
                self.status_signal.emit(
                    "Coincidence FPGA loaded successfully."
                )
    
            ssh.close()
    
        except Exception as e:
    
            self.status_signal.emit(
                "FPGA ERROR: " + str(e)
            )
                
            
            
            
        # ============================================================
# Main GUI
# ============================================================


class CoincidenceGUI(QWidget):


    def __init__(self):

        super().__init__()

        self.worker = None
        self.fpga_worker = None

        self.initUI()



    def initUI(self):

        self.setWindowTitle(
            "Red Pitaya Coincidence Counter"
        )


        self.resize(
            1150,
            800
        )


        main = QVBoxLayout()



        # --------------------------
        # Connection Settings
        # --------------------------

        settings = QGroupBox(
            "Acquisition Settings"
        )

        grid = QGridLayout()


        self.ip = QLineEdit(
            DEFAULT_IP
        )

        self.user = QLineEdit(
            DEFAULT_USER
        )

        self.password = QLineEdit(
            DEFAULT_PASSWORD
        )

        self.password.setEchoMode(
            QLineEdit.Password
        )


        self.duration = QSpinBox()

        self.duration.setRange(
            1,
            3600
        )

        self.duration.setValue(
            5
        )


        self.filename = QLineEdit(
            "coincidence_data.csv"
        )


        grid.addWidget(
            QLabel("Red Pitaya IP"),0,0
        )

        grid.addWidget(
            self.ip,0,1,1,3
        )


        grid.addWidget(
            QLabel("Username"),1,0
        )

        grid.addWidget(
            self.user,1,1
        )


        grid.addWidget(
            QLabel("Password"),1,2
        )

        grid.addWidget(
            self.password,1,3
        )


        grid.addWidget(
            QLabel("Time (s)"),2,0
        )

        grid.addWidget(
            self.duration,2,1
        )


        grid.addWidget(
            QLabel("Filename"),2,2
        )

        grid.addWidget(
            self.filename,2,3
        )


        settings.setLayout(grid)

    
        # --------------------------
        # Buttons
        # --------------------------




        # FPGA button row

        fpga_layout = QHBoxLayout()
        
        self.load_fpga = QPushButton(
            "LOAD FPGA Image"
        )
        
        self.load_fpga.setMinimumHeight(55)
        self.load_fpga.setMinimumWidth(250)
        
        fpga_layout.addWidget(
            self.load_fpga
        )
        
        
        # START STOP COPY row
        
        buttons = QHBoxLayout()
        
        
        self.start = QPushButton(
            "START"
        )
        
        self.stop = QPushButton(
            "STOP"
        )
        
        self.copy = QPushButton(
            "COPY DATA"
        )
        
        
        self.start.setMinimumHeight(45)
        self.stop.setMinimumHeight(45)
        self.copy.setMinimumHeight(45)
        
        
        buttons.addWidget(self.start)
        buttons.addWidget(self.stop)
        buttons.addWidget(self.copy)



       # --------------------------
        # Plot
        # --------------------------

        self.plot = pg.PlotWidget()
        
        self.plot.setBackground(
            "w"
        )
        
        self.plot.showGrid(
            x=True,
            y=True
        )
        
        self.plot.setLabel(
            "bottom",
            "Time (s)"
        )
        
        self.plot.setLabel(
            "left",
            "Count rate (Hz)"
        )
        
        self.plot.addLegend()
        
        
        self.plot.enableAutoRange(
            axis='x',
            enable=False
        )
        
        self.plot.enableAutoRange(
            axis='y',
            enable=True
        )
        
        
        # ==========================
        # Right Y-axis setup
        # ==========================
        
        self.plot.showAxis('right')
        
        self.plot.setLabel(
            'right',
            'Coincidences (Hz)'
        )
        
        right_axis = self.plot.getAxis('right')

        
        
        right_axis.setTextPen(
            pg.mkPen('b')
        )
        
        
        
        self.rightView = pg.ViewBox()
        
        self.plot.scene().addItem(
            self.rightView
        )
        
        
        self.plot.getAxis('right').linkToView(
            self.rightView
        )
        
        self.rightView.setXLink(
            self.plot
        )
        
        
        def updateViews():
        
            self.rightView.setGeometry(
                self.plot.getViewBox().sceneBoundingRect()
            )
        
            self.rightView.linkedViewChanged(
                self.plot.getViewBox(),
                self.rightView.XAxis
            )
        
        
        updateViews()
        
        
        self.plot.getViewBox().sigResized.connect(
            updateViews
        )
        
        
        # ==========================
        # Left Y-axis plots
        # ==========================
        
        self.lineA = self.plot.plot(
            [],
            [],
            pen=pg.mkPen('b', width=3),
            name="Singles A"
        )
        
        
        self.lineB = self.plot.plot(
            [],
            [],
            pen=pg.mkPen('g', width=3),
            name="Singles B"
        )
        
        
        # ==========================
        # Right Y-axis plot
        # ==========================
        
        self.lineC = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen('r', width=3),
            name="Coincidences"
        )
        
        self.rightView.addItem(
            self.lineC
        )

        # --------------------------
        # Status
        # --------------------------

        self.counts = QLabel(
            "A:0   B:0   Coinc:0"
        )


        self.progress = QProgressBar()


        self.status = QTextEdit()

        self.status.setReadOnly(
            True
        )

        self.status.setMaximumHeight(
            140
        )



        main.addWidget(settings)

        main.addLayout(fpga_layout)

        main.addLayout(buttons)

        main.addWidget(self.plot)

        main.addWidget(self.counts)

        main.addWidget(self.progress)

        main.addWidget(self.status)


        self.setLayout(main)



        # Connections
        self.copy.clicked.connect(
            self.copy_data
        )

        self.start.clicked.connect(
            self.start_run
        )

        self.stop.clicked.connect(
            self.stop_run
        )

        self.load_fpga.clicked.connect(
            self.load_fpga_image
        )


        self.plot.getAxis(
            'left'
        ).enableAutoSIPrefix(False)



        self.x=[]
        self.a=[]
        self.b=[]
        self.c=[]

    # ============================================================
    # COPY DATA FROM RED PITAYA
    # ============================================================
    
    def copy_data(self):
    
        try:
    
            self.log(
                "Copying data file..."
            )
    
    
            filename = self.filename.text()
    
    
            ssh = paramiko.SSHClient()
    
            ssh.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
    
    
            ssh.connect(
                hostname=self.ip.text(),
                username=self.user.text(),
                password=self.password.text(),
                timeout=5
            )
    
            stdin, stdout, stderr = ssh.exec_command(
                "pwd; ls -l; find / -name coincidence_data.csv 2>/dev/null"
            )
            
            print(stdout.read().decode())
            print(stderr.read().decode())
            
            with SCPClient(
                ssh.get_transport()
            ) as scp:
    
                scp.get(
                    filename,
                    filename
                )
    
    
            ssh.close()
    
    
            self.log(
                f"File copied successfully: {filename}"
            )
    
    
        except Exception as e:
    
    
            self.log(
                "COPY ERROR: " + str(e)
            )


    def log(self,text):

        self.status.append(
            text
        )
        # ============================================================
    # START acquisition
    # ============================================================

    def start_run(self):

        self.x.clear()
        self.a.clear()
        self.b.clear()
        self.c.clear()

        self.lineA.clear()
        self.lineB.clear()
        self.lineC.setData([], [])

        self.progress.setValue(0)

        self.status.clear()


        self.worker = SSHWorker(
            self.ip.text(),
            self.user.text(),
            self.password.text(),
            self.duration.value(),
            self.filename.text()
        )


        self.worker.data_signal.connect(
            self.update_plot
        )

        self.worker.status_signal.connect(
            self.log
        )

        self.worker.finished_signal.connect(
            self.acquisition_finished
        )

        self.worker.finished.connect(
            self.worker.deleteLater
        )
        self.worker.start()



    # ============================================================
    # Update live plot + counts + log
    # ============================================================

    def update_plot(self,t,c,a,b):


        self.x.append(t)
        self.a.append(a)
        self.b.append(b)
        self.c.append(c)


        self.lineA.setData(
            self.x,
            self.a
        )

        self.lineB.setData(
            self.x,
            self.b
        )

        self.lineC.setData(
            self.x,
            self.c
        )
        self.rightView.enableAutoRange(axis=pg.ViewBox.YAxis)

        self.plot.setXRange(
            0,
            self.duration.value()
        )


        self.counts.setText(
            f"Singles A : {a:,.0f} Hz     "
            f"Singles B : {b:,.0f} Hz     "
            f"Coincidences : {c:,.0f} Hz"
        )


        self.log(
            f"{t:.2f}s | "
            f"A={a:.0f} Hz | "
            f"B={b:.0f} Hz | "
            f"Coinc={c:.0f} Hz"
        )


        percent = min(
            int(100*t/self.duration.value()),
            100
        )

        self.progress.setValue(
            percent
        )



    # ============================================================
    # Acquisition finished
    # ============================================================

    def acquisition_finished(self):

        self.progress.setValue(100)
    
        self.log("Acquisition finished")
    
        if self.worker:
    
            self.worker.quit()
            self.worker.wait()
    
            self.worker.deleteLater()
    
            self.worker = None


    # ============================================================
    # STOP button
    # ============================================================

    def stop_run(self):

        if self.worker:

            self.worker.stop()

            self.log(
                "Acquisition stopped"
            )



    # ============================================================
    # FPGA image loading
    # ============================================================

    def load_fpga_image(self):


        self.fpga_worker = FPGAWorker(
            self.ip.text(),
            self.user.text(),
            self.password.text()
        )


        self.fpga_worker.status_signal.connect(
            self.log
        )


        self.fpga_worker.start()



    # ============================================================
    # Close GUI safely
    # ============================================================

    def closeEvent(self,event):


        if self.worker:

            self.worker.stop()

            self.worker.wait()



        if self.fpga_worker:

            self.fpga_worker.quit()

            self.fpga_worker.wait()



        event.accept()



# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    print("Starting QApplication")

    app = QApplication(sys.argv)

    print("Creating GUI")

    gui = CoincidenceGUI()

    print("Showing GUI")

    gui.show()

    print("Entering event loop")

    app.exec_()

    print("Event loop ended")