"""
Test suite for Platform Paths module.

This test suite validates cross-platform path handling and file operations
including path normalization, joining, and platform-specific behaviors.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
from pathlib import Path, PureWindowsPath, PurePosixPath

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.platform_paths import (
    PlatformPathHandler, Platform, PathConfig,
    get_platform_handler, normalize_path, join_paths,
    find_executable, get_config_directory, get_data_directory,
    is_windows, is_posix
)


class TestPlatformPathHandler(unittest.TestCase):
    """Test cases for PlatformPathHandler class"""

    def setUp(self):
        """Set up test fixtures"""
        self.handler = PlatformPathHandler()

    def test_detect_platform_windows(self):
        """Test Windows platform detection"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            self.assertEqual(handler.platform, Platform.WINDOWS)

    def test_detect_platform_posix(self):
        """Test POSIX platform detection"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            self.assertEqual(handler.platform, Platform.POSIX)

    def test_windows_path_config(self):
        """Test Windows path configuration"""
        with patch('os.name', 'nt'):
            with patch.dict(os.environ, {
                'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
                'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'
            }):
                handler = PlatformPathHandler()
                config = handler.config

                self.assertEqual(config.path_separator, '\\')
                self.assertEqual(config.executable_extension, '.exe')
                self.assertEqual(config.script_extension, '.bat')
                self.assertEqual(config.library_extension, '.dll')
                self.assertFalse(config.case_sensitive)

    def test_posix_path_config(self):
        """Test POSIX path configuration"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            config = handler.config

            self.assertEqual(config.path_separator, '/')
            self.assertEqual(config.executable_extension, '')
            self.assertEqual(config.script_extension, '.sh')
            self.assertEqual(config.library_extension, '.so')
            self.assertTrue(config.case_sensitive)

    def test_normalize_path_windows(self):
        """Test Windows path normalization"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()

            # Test POSIX to Windows conversion
            posix_path = Path('/usr/local/bin')
            normalized = handler.normalize_path(posix_path)
            self.assertIsInstance(normalized, Path)

            # Test string path
            string_path = 'C:\\Users\\Test\\Documents'
            normalized = handler.normalize_path(string_path)
            self.assertEqual(str(normalized).upper(), string_path.upper())  # Case insensitive

    def test_normalize_path_posix(self):
        """Test POSIX path normalization"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()

            # Test Windows to POSIX conversion
            windows_path = PureWindowsPath('C:\\Users\\Test\\Documents')
            normalized = handler.normalize_path(windows_path)
            self.assertNotIn('\\', str(normalized))

            # Test string path
            string_path = '/usr/local/bin'
            normalized = handler.normalize_path(string_path)
            self.assertEqual(str(normalized), string_path)

    def test_join_paths_windows(self):
        """Test Windows path joining"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()

            result = handler.join_paths('C:', 'Users', 'Test', 'Documents')
            # Should contain backslashes on Windows
            self.assertTrue('\\' in str(result))

    def test_join_paths_posix(self):
        """Test POSIX path joining"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()

            result = handler.join_paths('/', 'usr', 'local', 'bin')
            self.assertEqual(str(result), '/usr/local/bin')

    def test_get_executable_path_windows(self):
        """Test Windows executable path generation"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            result = handler.get_executable_path('python')
            self.assertEqual(result.name, 'python.exe')
            self.assertTrue(str(result).endswith('.exe'))

    def test_get_executable_path_posix(self):
        """Test POSIX executable path generation"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            result = handler.get_executable_path('python')
            self.assertEqual(result.name, 'python')
            self.assertFalse(str(result).endswith('.exe'))

    def test_get_script_path_windows(self):
        """Test Windows script path generation"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            result = handler.get_script_path('setup')
            self.assertEqual(result.name, 'setup.bat')

    def test_get_script_path_posix(self):
        """Test POSIX script path generation"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            result = handler.get_script_path('setup')
            self.assertEqual(result.name, 'setup.sh')

    def test_get_library_path_windows(self):
        """Test Windows library path generation"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            result = handler.get_library_path('test')
            self.assertEqual(result.name, 'test.dll')

    def test_get_library_path_posix(self):
        """Test POSIX library path generation"""
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            result = handler.get_library_path('test')
            self.assertTrue(result.name.endswith('.so'))

    @patch.dict(os.environ, {'PATH': '/usr/bin:/bin'})
    @patch('os.access')
    @patch('os.path.exists')
    def test_find_executable_found(self, mock_exists, mock_access):
        """Test finding executable in PATH"""
        mock_exists.return_value = True
        mock_access.return_value = True

        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            result = handler.find_executable('python')

            # Should find the executable
            self.assertIsNotNone(result)

    @patch.dict(os.environ, {'PATH': '/usr/bin:/bin'})
    @patch('os.access')
    @patch('os.path.exists')
    def test_find_executable_not_found(self, mock_exists, mock_access):
        """Test not finding executable in PATH"""
        mock_exists.return_value = False
        mock_access.return_value = False

        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            result = handler.find_executable('nonexistent')

            # Should return None for non-existent executable
            self.assertIsNone(result)

    def test_get_temp_directory(self):
        """Test temporary directory creation"""
        with patch('tempfile.gettempdir', return_value='/tmp'):
            handler = PlatformPathHandler()
            temp_dir = handler.get_temp_directory('test_')

            # Should be a Path object with correct prefix
            self.assertIsInstance(temp_dir, Path)
            self.assertTrue(temp_dir.name.startswith('test_'))
            self.assertIn('tmp', str(temp_dir))

    def test_get_config_directory_windows(self):
        """Test Windows config directory path"""
        with patch('os.name', 'nt'):
            with patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
                with patch.object(PlatformPathHandler, 'create_directory') as mock_create:
                    handler = PlatformPathHandler()
                    config_dir = handler.get_config_directory('testapp')

                    expected = Path('C:\\Users\\Test\\AppData\\Roaming\\testapp')
                    self.assertEqual(config_dir, expected)
                    mock_create.assert_called_once()

    def test_get_config_directory_posix(self):
        """Test POSIX config directory path"""
        with patch('os.name', 'posix'):
            with patch('os.path.expanduser') as mock_expand:
                mock_expand.side_effect = lambda x: x.replace('~', '/home/test')
                with patch.object(PlatformPathHandler, 'create_directory') as mock_create:
                    handler = PlatformPathHandler()
                    config_dir = handler.get_config_directory('testapp')

                    expected = Path('/home/test/.config/testapp')
                    self.assertEqual(config_dir, expected)
                    mock_create.assert_called_once()

    def test_case_sensitive_detection(self):
        """Test case sensitivity detection"""
        # Windows
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            self.assertFalse(handler.is_case_sensitive())

        # POSIX
        with patch('os.name', 'posix'):
            handler = PlatformPathHandler()
            self.assertTrue(handler.is_case_sensitive())

    def test_path_length_validation(self):
        """Test path length validation"""
        # Short path - should be valid
        short_path = '/usr/bin'
        self.assertTrue(self.handler.validate_path_length(short_path))

        # Very long path - should be invalid on Windows
        very_long_path = 'a' * 300
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            self.assertFalse(handler.validate_path_length(very_long_path))

    def test_get_relative_path(self):
        """Test relative path calculation"""
        base = Path('/home/user')
        target = Path('/home/user/documents/file.txt')

        result = self.handler.get_relative_path(target, base)
        self.assertEqual(result, Path('documents/file.txt'))

        # Test when target is not relative to base
        unrelated = Path('/etc/config')
        result = self.handler.get_relative_path(unrelated, base)
        self.assertEqual(result, unrelated.absolute())

    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_copy_file_success(self, mock_makedirs, mock_copy):
        """Test successful file copying"""
        mock_copy.return_value = None

        src = Path('/source/file.txt')
        dst = Path('/dest/file.txt')

        result = self.handler.copy_file(src, dst)

        self.assertTrue(result)
        mock_copy.assert_called_once()

    @patch('shutil.copy2')
    def test_copy_file_failure(self, mock_copy):
        """Test file copying failure"""
        mock_copy.side_effect = Exception('Copy failed')

        src = Path('/source/file.txt')
        dst = Path('/dest/file.txt')

        result = self.handler.copy_file(src, dst)

        self.assertFalse(result)

    @patch('shutil.move')
    @patch('os.makedirs')
    def test_move_file_success(self, mock_makedirs, mock_move):
        """Test successful file moving"""
        mock_move.return_value = None

        src = Path('/source/file.txt')
        dst = Path('/dest/file.txt')

        result = self.handler.move_file(src, dst)

        self.assertTrue(result)
        mock_move.assert_called_once()

    def test_make_executable_posix(self):
        """Test making file executable on POSIX"""
        with patch('os.name', 'posix'):
            with patch('os.stat') as mock_stat:
                with patch('os.chmod') as mock_chmod:
                    mock_stat.return_value.st_mode = 0o644

                    handler = PlatformPathHandler()
                    result = handler.make_executable('/test/script.sh')

                    self.assertTrue(result)
                    mock_chmod.assert_called_once()

    def test_make_executable_windows(self):
        """Test making file executable on Windows (no-op)"""
        with patch('os.name', 'nt'):
            handler = PlatformPathHandler()
            result = handler.make_executable('C:\\test\\script.bat')

            self.assertTrue(result)  # Should return True without doing anything

    def test_get_file_type(self):
        """Test file type detection"""
        test_cases = [
            ('script.py', 'text/x-python'),
            ('config.json', 'application/json'),
            ('document.md', 'text/markdown'),
            ('executable.exe', 'application/x-executable'),
            ('unknown.xyz', 'application/octet-stream'),
        ]

        for filename, expected_type in test_cases:
            with self.subTest(filename=filename):
                result = self.handler.get_file_type(filename)
                self.assertEqual(result, expected_type)

    @patch.dict(os.environ, {'PATH': '/usr/bin:/bin:/usr/local/bin'})
    def test_get_environment_paths(self):
        """Test getting environment PATH entries"""
        paths = self.handler.get_environment_paths()
        expected = ['/usr/bin', '/bin', '/usr/local/bin']
        self.assertEqual(paths, expected)

    def test_get_user_paths_windows(self):
        """Test getting Windows user directories"""
        with patch('os.name', 'nt'):
            with patch.dict(os.environ, {
                'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming',
                'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local',
                'ProgramFiles': 'C:\\Program Files'
            }):
                with patch('os.path.expanduser') as mock_expand:
                    mock_expand.side_effect = lambda x: x.replace('~', 'C:\\Users\\Test')

                    handler = PlatformPathHandler()
                    user_paths = handler.get_user_paths()

                    self.assertIn('home', user_paths)
                    self.assertIn('appdata', user_paths)
                    self.assertIn('localappdata', user_paths)
                    self.assertIn('program_files', user_paths)

    def test_create_platform_script_windows(self):
        """Test creating Windows platform script"""
        commands = ['echo Hello', 'echo World']
        output_path = Path('/test/script.bat')

        with patch('os.name', 'nt'):
            with patch.object(PlatformPathHandler, 'create_directory') as mock_create:
                with patch('builtins.open', create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value.__enter__.return_value = mock_file

                    handler = PlatformPathHandler()
                    result = handler.create_platform_script(commands, output_path)

                    self.assertTrue(result)
                    mock_create.assert_called_once()
                    mock_open.assert_called_once()

    def test_create_platform_script_posix(self):
        """Test creating POSIX platform script"""
        commands = ['echo Hello', 'echo World']
        output_path = Path('/test/script.sh')

        with patch('os.name', 'posix'):
            with patch.object(PlatformPathHandler, 'create_directory') as mock_create:
                with patch.object(PlatformPathHandler, 'make_executable') as mock_exec:
                    with patch('builtins.open', create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_open.return_value.__enter__.return_value = mock_file

                        handler = PlatformPathHandler()
                        result = handler.create_platform_script(commands, output_path)

                        self.assertTrue(result)
                        mock_create.assert_called_once()
                        mock_exec.assert_called_once()


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""

    def test_get_platform_handler_singleton(self):
        """Test that get_platform_handler returns singleton"""
        handler1 = get_platform_handler()
        handler2 = get_platform_handler()
        self.assertIs(handler1, handler2)

    @patch('utils.platform_paths.get_platform_handler')
    def test_normalize_path_function(self, mock_handler):
        """Test normalize_path convenience function"""
        mock_handler.return_value.normalize_path.return_value = Path('/test/path')
        result = normalize_path('/test/path')
        mock_handler.return_value.normalize_path.assert_called_once_with('/test/path')

    @patch('utils.platform_paths.get_platform_handler')
    def test_join_paths_function(self, mock_handler):
        """Test join_paths convenience function"""
        mock_handler.return_value.join_paths.return_value = Path('/test/path')
        result = join_paths('/test', 'path')
        mock_handler.return_value.join_paths.assert_called_once_with('/test', 'path')

    @patch('utils.platform_paths.get_platform_handler')
    def test_find_executable_function(self, mock_handler):
        """Test find_executable convenience function"""
        mock_handler.return_value.find_executable.return_value = Path('/usr/bin/python')
        result = find_executable('python')
        mock_handler.return_value.find_executable.assert_called_once_with('python')

    @patch('utils.platform_paths.get_platform_handler')
    def test_get_config_directory_function(self, mock_handler):
        """Test get_config_directory convenience function"""
        mock_handler.return_value.get_config_directory.return_value = Path('/config')
        result = get_config_directory('testapp')
        mock_handler.return_value.get_config_directory.assert_called_once_with('testapp')

    @patch('utils.platform_paths.get_platform_handler')
    def test_get_data_directory_function(self, mock_handler):
        """Test get_data_directory convenience function"""
        mock_handler.return_value.get_data_directory.return_value = Path('/data')
        result = get_data_directory('testapp')
        mock_handler.return_value.get_data_directory.assert_called_once_with('testapp')

    @patch('utils.platform_paths.get_platform_handler')
    def test_is_windows_function(self, mock_handler):
        """Test is_windows convenience function"""
        mock_handler.return_value.platform = Platform.WINDOWS
        result = is_windows()
        self.assertTrue(result)

    @patch('utils.platform_paths.get_platform_handler')
    def test_is_posix_function(self, mock_handler):
        """Test is_posix convenience function"""
        mock_handler.return_value.platform = Platform.POSIX
        result = is_posix()
        self.assertTrue(result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        self.handler = PlatformPathHandler()

    def test_empty_path_joining(self):
        """Test joining empty paths"""
        result = self.handler.join_paths()
        self.assertIsInstance(result, Path)

    def test_path_with_none_values(self):
        """Test path operations with None values"""
        # Should handle gracefully or raise appropriate error
        with self.assertRaises((TypeError, AttributeError)):
            self.handler.normalize_path(None)

    def test_copy_nonexistent_file(self):
        """Test copying non-existent file"""
        src = Path('/nonexistent/file.txt')
        dst = Path('/dest/file.txt')

        result = self.handler.copy_file(src, dst)
        self.assertFalse(result)

    def test_move_nonexistent_file(self):
        """Test moving non-existent file"""
        src = Path('/nonexistent/file.txt')
        dst = Path('/dest/file.txt')

        result = self.handler.move_file(src, dst)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()