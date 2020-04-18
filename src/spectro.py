#!/usr/bin/python3
# -*- coding: utf-8 -*-
# #########################################################################
# Spectro v0.9
#   Olivier Boesch (c) 2019
#   Secomam s250 and Prim Spectrometers software
#   Licence: MIT
# #########################################################################

# ------- software version
__version__ = '0.9'
# ------- dont write on console (file log only)
import os
os.environ["KIVY_NO_CONSOLELOG"] = "1"

# -------- kivy config : desktop app, maximized window, mouse and not multitouch
from kivy.config import Config
Config.set('kivy', 'desktop', 1)
Config.set('graphics', 'window_state', 'maximized')
Config.set('input', 'mouse', 'mouse,disable_multitouch')

# ------- kivy import
import kivy
kivy.require('1.10.1')
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from src.graph import SmoothLinePlot
from src import s250Prim_async
from serial.tools import list_ports
from src.utilities import get_bounds_and_ticks

# ------- graph theme for display and printing
# print_graph_theme = {'graph_area': {'label_options': {
# 'color': rgb('000000'),  # color of tick labels and titles
# 'bold': True},
# 'background_color': rgb('ffffff'),  # back ground color of canvas
# 'tick_color': rgb('000000'),  # ticks and grid
# 'border_color': rgb('000000')},  # border drawn around each graph
# 'plot_color': rgb('000000')}

# display_graph_theme = {'graph_area': {'label_options': {
# 'color': rgb('ffffff'),  # color of tick labels and titles
# 'bold': True},
# 'background_color': rgb('000000'),  # back ground color of canvas
# 'tick_color': rgb('ffffff'),  # ticks and grid
# 'border_color': rgb('ffffff')},  # border drawn around each graph
# 'plot_color': rgb('ffffff')}


# ------ Popup window for wavelength bounds in spectrum part
class PopupWavelengthSpectrum(Popup):
    """wavelengths selection for spectrum"""

    def when_opened(self):
        """what to do to initialize view"""
        # get bounds of spectrometer and apply
        min, max = sapp.get_wavelength_bounds()
        self.ids['wlstart_sldr'].min = min
        self.ids['wlstart_sldr'].max = max
        self.ids['wlend_sldr'].min = min
        self.ids['wlend_sldr'].max = max
        # get current values and apply
        start, end = sapp.get_wavelength_spectrum()
        self.ids['wlstart_sldr'].value = start
        self.ids['wlend_sldr'].value = end

    def on_ok(self):
        """if user validates, set to internal values and close popup"""
        start = self.ids['wlstart_sldr'].value
        end = self.ids['wlend_sldr'].value
        sapp.set_wavelength_spectrum(start, end)
        self.dismiss()

    def on_cancel(self):
        """if user invalidates, just close"""
        self.dismiss()

    def on_reset(self):
        """reset values to bounds"""
        min, max = sapp.get_wavelength_bounds()
        self.ids['wlstart_sldr'].value = min
        self.ids['wlend_sldr'].value = max

    def value_changed(self, who_has_changed):
        """restict changes : max must be >= min"""
        if self.ids['wlend_sldr'].value < self.ids['wlstart_sldr'].value:
            if who_has_changed == 'start':
                self.ids['wlend_sldr'].value = self.ids['wlstart_sldr'].value
            if who_has_changed == 'end':
                self.ids['wlstart_sldr'].value = self.ids['wlend_sldr'].value


# ------ Popup window for wavelength selection in absorbance part
class PopupWavelengthAbs(Popup):
    """wavelength selection for absorbance"""

    def when_opened(self):
        """what to do to initialize view"""
        # get bounds of spectrometer and apply them
        min, max = sapp.get_wavelength_bounds()
        self.ids['wl_sldr'].min = min
        self.ids['wl_sldr'].max = max
        # get current value and apply it
        val = sapp.get_wavelength_abs()
        self.ids['wl_sldr'].value = val

    def on_ok(self):
        """if user validates, set to internal value and close popup"""
        val = self.ids['wl_sldr'].value
        self.dismiss()
        sapp.set_wavelength_abs(val)

    def on_cancel(self):
        """if user invalidates, just close popup"""
        self.dismiss()


# ------ About... Popup window
class AboutPopup(Popup):
    """About spectro popup"""

    def when_opened(self):
        """when opened, get version number and add it to text"""
        self.ids['about_lbl'].text = 'version : ' + __version__ + '\n' + self.ids['about_lbl'].text


# ------- Popup for message notification
class PopupMessage(Popup):
    """PopupMessage : display a message box"""

    def when_opened(self):
        pass

    def set_message(self, title, text):
        """set_message: set title and text"""
        self.title = title
        self.ids['message_content_lbl'].text = text

    def get_message(self):
        """get_message: get title and text"""
        return self.title, self.ids['message_content_lbl'].text

    def close_after(self, dt=1.):
        """close popup automaticaly after a short time (us 1s)"""
        Clock.schedule_once(lambda t: self.dismiss(), dt)


# ------- Popup for operation running (no dismiss)
class PopupOperation(Popup):
    """display a popup while an operation occures"""

    def when_opened(self):
        pass

    def update(self, title, text):
        """set title and text"""
        self.ids['message_operation_lbl'].text = text
        self.title = title

    def close_after(self, dt=2.):
        """close popup automaticaly after a short time (us 1s)"""
        Clock.schedule_once(lambda t: self.dismiss(), dt)


# ------- Popup for operation running (no dismiss) with a progress bar
class PopupProgress(Popup):
    """like operation popup but with a progress bar"""

    def when_opened(self):
        pass

    def update(self, title, text, progress):
        """set title, progress and text"""
        self.ids['message_progress_lbl'].text = text
        self.title = title
        self.ids['progress_progress_pb'].value = progress

    def close_after(self, dt=1.):
        """close popup automatically after a short time (us 1s)"""
        Clock.schedule_once(lambda t: self.dismiss(), dt)


# ------- Application part for spectrum (graph, export buttons)
class BoxSpectrum(BoxLayout):
    """displays a box layout"""
    type = 'spectrum'

    def init(self, wlmin, wlmax):
        self.ids['graph_widget'].xmin = wlmin
        self.ids['graph_widget'].xmax = wlmax
        self.ids['boxspectrum_title_lbl'].text = 'Mesure de spectre de %d nm \u00e0 %d nm' % (wlmin, wlmax)

# ------- Application part for absorbance (graph, export buttons)
class BoxAbs(BoxLayout):
    type = 'abs'

    def init(self, wl):
        self.ids['boxabs_title_lbl'].text = 'Mesure d\'absorbance \u00e0 %d nm' % (wl,)


# ------- Main App Class
class SpectroApp(App):
    port = None
    spectro = s250Prim_async.S250Prim()
    wl_min = spectro.waveLengthLimits['start']
    wl_max = spectro.waveLengthLimits['end']
    wl_abs = spectro.waveLengthLimits['start']
    data_widget = None
    timeout_number = 0
    event_spectro_cmd = None
    data_points = None
    current_popup = None
    update_ports_list_event = None
    max_data = 0.

    def send_command(self, cmd_func, clbck_ok, clbck_error):
        """sends a command to the spectrometer and schedule a verification function"""
        check_freq = 60  # Hz - check frequency (max 60Hz -> once per frame)
        cmd_timeout = 120  # s - timeout to get a valid answer
        # proceed only if the spectrometer is connected. return false otherwise
        if self.spectro.connected:
            try:
                self.timeout_number = check_freq * cmd_timeout  # stop schedule after cmd_timeout s
                self.root.ids['led_out'].state = 'on'
                # send command and get number of bytes to be received
                cmd_data = cmd_func()
                # don't schedule if command need 0 bytes as answer
                if cmd_data[1] != 0:
                    self.event_spectro_cmd = Clock.schedule_interval(
                        lambda dt: self.check_command_result(cmd_data, clbck_ok, clbck_error), 1. / check_freq)
                return True
            except:
                # cancel check_command_result scheduling
                self.event_spectro_cmd.cancel()
                # set ui in disconnect state
                self.set_disconnected_ui_state()
                # call error callback
                clbck_error()
                return False
        return False

    def check_command_result(self, cmd_data, clbck_ok, clbck_error):
        """check if the number of bytes is ok for processing command"""
        cmd_sent, n_return = cmd_data
        # get number of bytes waiting in input buffer
        try:
            n_waiting = self.spectro.conn.in_waiting
        # if cant read but connected (sudden disconnection)
        except:
            # cancel check_command_result scheduling
            self.event_spectro_cmd.cancel()
            # set ui in disconnect state
            self.set_disconnected_ui_state()
            # call error callback
            clbck_error()
            return
        # if enough bytes waiting for what we need to read
        if n_waiting >= n_return:
            self.root.ids['led_in'].state = 'on'
            # cancel check_command_result scheduling (no more need to try)
            self.event_spectro_cmd.cancel()
            # read the bytes we need (no more)
            data = self.spectro.receive(n_return)
            # send to spectrometer library to proceed raw data
            ans = self.spectro.return_command(data, cmd_sent)
            # call success callback
            clbck_ok(ans)
        else:
            self.timeout_number -= 1
            # if timeout happened
            if self.timeout_number == 0:
                # cancel check_command_result scheduling (too late to try)
                self.event_spectro_cmd.cancel()
                # set as disconnect for ui
                self.set_disconnected_ui_state()
                # call error callback
                clbck_error()

    def build(self):
        # update ports list now
        self.update_ports_list()
        # update ports list every 5s
        self.update_ports_list_event = Clock.schedule_interval(lambda dt: self.update_ports_list(), 5.)

    def on_ports_list_text(self, value):
        """update internal port value"""
        self.port = value

    def update_ports_list(self):
        """get available serial ports and set ports_list spinner values"""
        # get an iterator with available serial ports
        comportslist = list_ports.comports()
        # make a tuple and set spinner values
        self.root.ids['ports_list'].values = tuple([item.device for item in comportslist])
        # if current value is not in list then go back to default
        if self.root.ids['ports_list'].text not in self.root.ids['ports_list'].values:
            self.root.ids['ports_list'].text = 'Port S\u00e9rie'
            self.port = None
        # if no available serial port then tell the user
        if len(self.root.ids['ports_list'].values) == 0:
            self.root.ids['ports_list'].text = 'Pas de port S\u00e9rie'
            self.port = None
        # if only one port available select it by default
        elif len(self.root.ids['ports_list'].values) == 1:
            self.root.ids['ports_list'].text = self.root.ids['ports_list'].values[0]
            self.port = self.root.ids['ports_list'].values[0]

    def show_message(self, title: str, message: str, close_timeout: float = 2.0):
        p = PopupMessage()
        p.set_message(title, message)
        p.open()
        p.close_after(close_timeout)

    def load_display_spectrum(self, collapse):
        # spectrum accordion collapsed -> remove graph
        if collapse:
            self.root.ids['mainlayout'].remove_widget(self.data_widget)
            del (self.data_widget)
            self.data_widget = None
            self.root.ids['blank_spectrum_btn'].disabled = True
            self.root.ids['measure_spectrum_btn'].disabled = True
            self.root.ids['wavelength_spectrum_Lbl'].text = '--- - --- nm'
            self.data_points = None

        else:
            self.data_widget = BoxSpectrum()
            self.root.ids['mainlayout'].add_widget(self.data_widget)
            self.wl_min = self.spectro.waveLengthLimits['start']
            self.wl_max = self.spectro.waveLengthLimits['end']

    def load_display_abs(self, collapse):
        if collapse:
            self.root.ids['mainlayout'].remove_widget(self.data_widget)
            del (self.data_widget)
            self.data_widget = None
            self.root.ids['blank_abs_btn'].disabled = True
            self.root.ids['measure_abs_btn'].disabled = True
            self.root.ids['wavelength_abs_lbl'].text = '--- nm'
        else:
            self.data_widget = BoxAbs()
            self.root.ids['mainlayout'].add_widget(self.data_widget)
            self.wl_abs = self.spectro.waveLengthLimits['start']

    def on_connect_btn_press(self):
        # if we are already connected then stop the spectro, disconnect serial port and reflact on ui
        if self.spectro.connected:
            self.send_command(self.spectro.stop_device, None, None)
            self.set_disconnected_ui_state()
        # if not, let's connect
        else:
            # is there a port selected ?
            if self.port is not None:
                # show as connected
                self.set_connected_ui_state()
                # try to connect
                if self.spectro.connect(self.port):
                    # if ok, open a modal popup to tell we're busy and what we do
                    self.current_popup = PopupOperation()
                    self.current_popup.open()
                    self.current_popup.update("Spectrom\u00e8tre", "Connexion en cours...")
                    self.send_command(self.spectro.start_device, self.on_connect_ok, self.on_connect_error)
                else:
                    # if not, tell there's something wrong
                    self.show_message('Erreur de connection', "Impossible de se connecter \u00e0 %d" % (self.port,))
                    self.set_disconnected_ui_state()
            else:
                # no port selected, tell user to choose one
                self.show_message("Erreur de connection", "Veuillez choisir le port s\u00e9rie à ouvrir")

    def on_connect_ok(self, ans):
        # tell that it's ok and close popup after a short time
        self.current_popup.update("Spectrom\u00e8tre", "Connexion en cours... OK!")
        self.current_popup.close_after()

    def on_connect_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur de communication", "Impossible de d\u00e9marrer le spectrom\u00e8tre.")

    def set_connected_ui_state(self):
        self.root.ids['autotest_btn'].disabled = False
        self.root.ids['hardware_infos_btn'].disabled = False
        self.root.ids['wavelength_abs_btn'].disabled = False
        self.root.ids['wavelength_spectrum_btn'].disabled = False
        self.root.ids['connect_btn'].text = "D\u00e9connecter"
        self.root.ids['infobox_lbl'].text = "Connect\u00e9 \n%s" % (self.port,)
        self.update_ports_list_event.cancel()

    def set_disconnected_ui_state(self):
        self.spectro.disconnect()
        self.root.ids['autotest_btn'].disabled = True
        self.root.ids['hardware_infos_btn'].disabled = True
        self.root.ids['wavelength_abs_btn'].disabled = True
        self.root.ids['blank_abs_btn'].disabled = True
        self.root.ids['measure_abs_btn'].disabled = True
        self.root.ids['wavelength_spectrum_btn'].disabled = True
        self.root.ids['blank_spectrum_btn'].disabled = True
        self.root.ids['measure_spectrum_btn'].disabled = True
        self.root.ids['connect_btn'].text = "Connecter"
        self.root.ids['infobox_lbl'].text = "D\u00e9connect\u00e9"
        self.update_ports_list()
        self.update_ports_list_event = Clock.schedule_interval(lambda dt: self.update_ports_list(), 5.)

    def on_wavelength_spectrum_btn_press(self):
        p = PopupWavelengthSpectrum()
        p.open()

    def set_wavelength_spectrum(self, start, end):
        start = int(start)
        end = int(end)
        self.wl_min = start
        self.wl_max = end
        self.root.ids['wavelength_spectrum_Lbl'].text = "%d - %d nm" % (start, end)
        self.root.ids['blank_spectrum_btn'].disabled = False
        self.root.ids['measure_spectrum_btn'].disabled = True
        self.data_widget.init(start, end)

    def get_wavelength_spectrum(self):
        return (self.wl_min, self.wl_max)

    def get_wavelength_bounds(self):
        return (self.spectro.waveLengthLimits['start'], self.spectro.waveLengthLimits['end'])

    def on_blank_spectrum_btn_press(self):
        cmd_ok = self.send_command(lambda: self.spectro.make_spectrum_baseline(self.wl_min, self.wl_max),
                                   self.on_blank_spectrum_ok, self.on_blank_spectrum_error)
        if cmd_ok:
            self.current_popup = PopupOperation()
            self.current_popup.open()
            self.current_popup.update("Spectre", "Mesure de la ligne de base...")
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_blank_spectrum_ok(self, ans):
        if ans:
            self.root.ids['measure_spectrum_btn'].disabled = False
            self.current_popup.update("Spectre", "Mesure de la ligne de base... OK!")
        self.current_popup.close_after()

    def on_blank_spectrum_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de mesurer la ligne de base.")

    def on_measure_spectrum_btn_press(self):
        cmd_ok = self.send_command(lambda: self.spectro.get_spectrum_header(), self.on_measure_spectrum_btn_press_ok,
                                   self.on_measure_spectrum_btn_press_error)
        if cmd_ok:
            self.current_popup = PopupProgress()
            self.current_popup.open()
            self.current_popup.update("Spectre", "Mesure du spectre...", 0.)
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_measure_spectrum_btn_press_ok(self, ans):
        wlStart, N = ans
        self.current_popup.update("Spectre", "Mesure du spectre (%d points)" % (N,), 0.)
        if self.data_points is not None:
            self.data_widget.ids['graph_widget'].remove_plot(self.data_points)
        self.data_points = SmoothLinePlot()
        self.data_widget.ids['graph_widget'].add_plot(self.data_points)
        self.data_widget.ids['graph_widget'].ymax = 0.000001
        self.get_spectrum_point()

    def on_measure_spectrum_btn_press_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de mesurer le spectre.")

    def get_spectrum_point(self):
        cmd_ok = self.send_command(lambda: self.spectro.get_spectrum_data(), self.on_get_spectrum_point_ok,
                                   self.on_measure_spectrum_btn_press_error)
        if not cmd_ok:
            self.current_popup.dismiss()
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_get_spectrum_point_ok(self, ans):
        data, i, N = ans
        self.data_points.points.append(data)
        self.current_popup.update("Spectre", "Mesure du spectre (%d/%d points)" % (i, N), float(i) / float(N) * 100.0)
        # raw min and max to keep data in the window
        self.data_widget.ids['graph_widget'].ymax = max(self.data_widget.ids['graph_widget'].ymax, data[1])
        self.data_widget.ids['graph_widget'].ymin = min(self.data_widget.ids['graph_widget'].ymin, data[1])
        if i < N:
            self.get_spectrum_point()
        else:
            # autoscale of graph with usable ticks for wavelength and absorbance data
            ymin, ymax, major_tick, minor_tick = get_bounds_and_ticks(self.data_widget.ids['graph_widget'].ymin,
                                                                      self.data_widget.ids['graph_widget'].ymax, 10)
            self.data_widget.ids['graph_widget'].ymin = ymin
            self.data_widget.ids['graph_widget'].ymax = ymax
            self.data_widget.ids['graph_widget'].y_ticks_major = major_tick
            self.data_widget.ids['graph_widget'].y_ticks_minor = minor_tick
            xmin, xmax, major_tick, minor_tick = get_bounds_and_ticks(self.data_widget.ids['graph_widget'].xmin,
                                                                      self.data_widget.ids['graph_widget'].xmax, 10)
            self.data_widget.ids['graph_widget'].xmin = xmin
            self.data_widget.ids['graph_widget'].xmax = xmax
            self.data_widget.ids['graph_widget'].x_ticks_major = major_tick
            self.data_widget.ids['graph_widget'].x_ticks_minor = minor_tick
            self.current_popup.update("Spectre", "Mesure du spectre (%d/%d points)" % (N, N), 100.0)
            self.current_popup.close_after()

    def save_spectrum(self, txt):
        options = self.data_widget.ids['spectrum_export_spinner'].values
        # export as png image
        if txt == options[0]:
            self.data_widget.ids['graph_widget'].export_to_png('screenshot.png')
            self.show_message('Export du graphique comme image', 'Fichier sauvegard\u00e9 sous \'screenshot.png\'')
        # export as csv data
        elif txt == options[1] and self.data_points is not None:
            data = self.data_points.points
            f = open('data.csv', 'w')
            f.write('# wavelength(nm); abs')
            for it in data:
                f.write(str('%d ; %f' % it).replace('.', ','))  # change decimal point to comma to fit with LOo Calc
            f.close()
            self.show_message('Export du graphique comme donn\u00e9es csv', 'Fichier sauvegard\u00e9 sous \'data.csv\'')
        options = self.data_widget.ids['spectrum_export_spinner'].text = 'Exporter'

    def on_wavelength_abs_btn_press(self):
        p = PopupWavelengthAbs()
        p.open()

    def get_wavelength_abs(self):
        return self.wl_abs

    def set_wavelength_abs(self, val):
        val = int(val)
        if self.send_command(lambda: self.spectro.set_abs_wavelength(val), self.on_set_wavelength_abs_ok,
                             self.on_set_wavelength_abs_error):
            self.current_popup = PopupOperation()
            self.current_popup.open()
            self.current_popup.update("Absorbance", "R\u00e9glage de la longueur d'onde \u00e0 %d nm..." % (val,))
            self.wl_abs = val
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_set_wavelength_abs_ok(self, ans):
        self.current_popup.update("Absorbance",
                                  "R\u00e9glage de la longueur d'onde \u00e0 %d nm... OK" % (self.wl_abs,))
        self.current_popup.close_after()
        self.root.ids['wavelength_abs_lbl'].text = "%d nm" % (self.wl_abs,)
        self.root.ids['blank_abs_btn'].disabled = False
        self.root.ids['measure_abs_btn'].disabled = True
        self.data_widget.ids['abs_data_ti'].text += "Longueur d\'onde r\u00e9gl\u00e9e \u00e0 %d nm.\n" % (self.wl_abs,)

    def on_set_wavelength_abs_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de r\u00e9gler la longueur d'onde d'aborbance")

    def on_blank_abs_btn_press(self):
        if self.send_command(lambda: self.spectro.get_abs_zero(), self.on_blank_abs_btn_press_ok,
                             self.on_blank_abs_btn_press_error):
            self.current_popup = PopupOperation()
            self.current_popup.open()
            self.current_popup.update("Absorbance", "Mesure du z\u00e9ro \u00e0 %d nm..." % (self.wl_abs,))
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_blank_abs_btn_press_ok(self, ans):
        self.root.ids['measure_abs_btn'].disabled = False
        if not self.send_command(lambda: self.spectro.get_abs_data(), self.on_blank_abs_btn_press_ok_data_ok,
                                 self.on_blank_abs_btn_press_ok_data_error):
            self.current_popup.dismiss()
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_blank_abs_btn_press_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de mesurer le z\u00e9ro d'absorbance")

    def on_blank_abs_btn_press_ok_data_ok(self, ans):
        val = ans[1]
        self.spectro.zero_data = val
        self.data_widget.ids['abs_data_ti'].text += "z\u00e9ro d'absorbance...ok.\n"
        self.current_popup.dismiss()

    def on_blank_abs_btn_press_ok_data_error(self):
        self.on_blank_abs_btn_press_error()

    def on_measure_abs_btn_press(self):
        if self.send_command(lambda: self.spectro.get_abs(), self.on_measure_abs_btn_press_ok,
                             self.on_measure_abs_btn_press_error):
            self.current_popup = PopupOperation()
            self.current_popup.open()
            self.current_popup.update("Absorbance", "Mesure de l'absorbance \u00e0 %d nm" % (self.wl_abs,))
        else:
            p = PopupMessage()
            p.open()
            p.set_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_measure_abs_btn_press_ok(self, ans):
        if not self.send_command(self.spectro.get_abs_data, self.on_measure_abs_btn_press_ok_data_ok,
                                 self.on_measure_abs_btn_press_error):
            self.current_popup.dismiss()
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_measure_abs_btn_press_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de mesurer l'absorbance")

    def on_measure_abs_btn_press_ok_data_ok(self, ans):
        val = ans[1]
        self.data_widget.ids[
            'abs_data_ti'].text += 'Valeur de l\'absorbance: %f\n' % (val,)
        self.current_popup.update("Absorbance", "Mesure de l'absorbance \u00e0 %d nm... OK" % (self.wl_abs,))
        self.current_popup.close_after()

    def on_measure_abs_btn_press_ok_data_error(self):
        self.on_blank_abs_btn_press_error()

    def on_autotest_btn_press(self):
        if self.send_command(self.spectro.perform_autotest, self.on_autotest_btn_press_ok,
                             self.on_autotest_btn_press_error):
            self.current_popup = PopupOperation()
            self.current_popup.open()
            self.current_popup.update("Autotest", "Autotest en cours...")
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_autotest_btn_press_ok(self, ans):
        if ans[0]:
            self.current_popup.update("Autotest", "Autotest en cours... OK!")
            self.current_popup.auto_dismiss = True
        else:
            self.current_popup.dismiss()
            self.show_message("Erreur.",
                              "Erreur d'autotest : Mauvaise configuration de la machine (Code: %d" % (ans[1],))

    def on_autotest_btn_press_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible de faire l'autotest")

    def on_hardware_infos_btn_press(self):
        if self.send_command(self.spectro.get_model_name, self.on_hardware_infos_btn_press_ok,
                             self.on_hardware_infos_btn_press_error):
            self.current_popup = PopupMessage()
            self.current_popup.open()
            self.current_popup.set_message("Informations mat\u00e9riel", "Spectrom\u00e8tre : ")
        else:
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_hardware_infos_btn_press_ok(self, ans):
        model = ans[0]
        title, text = self.current_popup.get_message()
        self.current_popup.set_message(title, text + model)
        if not self.send_command(self.spectro.get_firmware_version, self.on_hardware_infos_btn_press_ok_firmware_ok,
                                 self.on_hardware_infos_btn_press_ok_firmware_error):
            self.current_popup.dismiss()
            self.show_message("Erreur.", "Spectrom\u00e8tre non connect\u00e9.")

    def on_hardware_infos_btn_press_error(self):
        self.current_popup.dismiss()
        self.show_message("Erreur.", "Impossible d'obtenir le nom de mod\u00e8le et la version")

    def on_hardware_infos_btn_press_ok_firmware_ok(self, ans):
        title, text = self.current_popup.get_message()
        self.current_popup.set_message(title, text + "\nversion logiciel : %d" % (ans,))

    def on_hardware_infos_btn_press_ok_firmware_error(self):
        self.on_hardware_infos_btn_press_error()

    def on_about_btn_press(self):
        """on_about_btn_press : what to do when 'a propos...' button is pressed"""
        AboutPopup().open()

    def on_quit_btn_press(self):
        """on_quit_btn_press : what to do when 'quit' button is pressed"""
        self.stop()

    def on_stop(self):
        """on_stop : things to do when about to stop app"""
        if self.send_command(self.spectro.stop_device, None, None):
            self.spectro.disconnect()


# ------- start App
sapp = SpectroApp()
sapp.run()
