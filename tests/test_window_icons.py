import unittest
from unittest.mock import Mock, patch

import ui_utils


class SectionLogoTests(unittest.TestCase):
    def test_logo_background_is_opaque_and_matches_each_section(self):
        for section, color in ui_utils.COULEURS_FOND_LOGO.items():
            with self.subTest(section=section):
                logo = ui_utils.creer_logo_section(section)
                self.assertEqual(logo.getpixel((0, 0)), (*bytes.fromhex(color[1:]), 255))
                self.assertEqual(logo.size, (32, 32))


class WindowPositionTests(unittest.TestCase):
    def test_form_starts_at_bottom_edge_of_visible_navbar(self):
        window = Mock()
        parent = Mock()
        root = Mock()
        navbar = Mock()
        parent.winfo_toplevel.return_value = root
        root._sgd_navbar = navbar
        root.state.return_value = "normal"
        root.winfo_rootx.return_value = 120
        root.winfo_width.return_value = 1000
        navbar.winfo_rooty.return_value = 145
        navbar.winfo_height.return_value = 60

        ui_utils.placer_fenetre_sous_navbar(window, parent, 400, 650)

        window.geometry.assert_called_once_with("400x650+420+205")

    def test_password_form_is_centered_over_login_dialog_when_root_is_hidden(self):
        window = Mock()
        parent = Mock()
        root = Mock()
        parent.winfo_toplevel.return_value = root
        parent.winfo_x.return_value = 500
        parent.winfo_y.return_value = 250
        parent.winfo_width.return_value = 300
        parent.winfo_height.return_value = 250
        root.state.return_value = "withdrawn"

        ui_utils.placer_fenetre_sous_navbar(window, parent, 450, 390)

        window.geometry.assert_called_once_with("450x390+425+180")

    def test_window_is_centered_on_screen_when_no_parent_is_visible(self):
        window = Mock()
        window.winfo_screenwidth.return_value = 1920
        window.winfo_screenheight.return_value = 1080

        ui_utils.centrer_fenetre(window, 300, 350)

        window.geometry.assert_called_once_with("300x350+810+365")

    def test_window_is_centered_over_its_visible_parent(self):
        window = Mock()
        parent = Mock()
        parent.winfo_x.return_value = 100
        parent.winfo_y.return_value = 50
        parent.winfo_width.return_value = 1000
        parent.winfo_height.return_value = 700

        ui_utils.centrer_fenetre(window, 300, 350, parent)

        window.geometry.assert_called_once_with("300x350+450+225")


class WindowIconTests(unittest.TestCase):
    def test_sgd_logo_is_set_as_default_for_all_toplevel_windows(self):
        root = Mock()
        logo = object()
        with patch.object(ui_utils.tk, "PhotoImage", return_value=logo):
            ui_utils.configurer_icone_fenetre(root)

        root.iconphoto.assert_called_once_with(True, logo)
        self.assertIs(root._sgd_icon_photo, logo)

    def test_section_icon_is_scoped_to_its_window(self):
        window = Mock()
        logo = object()
        with patch("PIL.ImageTk.PhotoImage", return_value=logo):
            ui_utils.configurer_icone_fenetre(window, "revenus")

        window.iconphoto.assert_called_once_with(False, logo)
        self.assertIs(window._sgd_icon_photo, logo)


if __name__ == "__main__":
    unittest.main()
