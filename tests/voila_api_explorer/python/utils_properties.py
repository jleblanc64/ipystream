class PropertyValue:
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return self.data

    def __repr__(self):
        return f"PropertyValue({self.data!r})"


class Properties:
    def __init__(self):
        self.properties = {}

    def load(self, f):
        """Load properties from a file object opened in binary mode."""
        for line in f:
            # Decode bytes to string
            line = line.decode('utf-8', errors='ignore').strip()

            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('!'):
                continue

            # Handle line continuation (backslash at end)
            while line.endswith('\\') and not line.endswith('\\\\'):
                line = line[:-1]
                next_line = next(f, b'').decode('utf-8', errors='ignore').strip()
                line += next_line

            # Find the separator (=, :, or whitespace)
            sep_idx = -1
            for i, char in enumerate(line):
                if char in ('=', ':'):
                    sep_idx = i
                    break
                elif char.isspace():
                    sep_idx = i
                    break

            if sep_idx == -1:
                # No separator found, treat whole line as key with empty value
                key = line
                value = ''
            else:
                key = line[:sep_idx].strip()
                value = line[sep_idx + 1:].strip()

            # Unescape special characters
            key = self._unescape(key)
            value = self._unescape(value)

            # Store as PropertyValue object
            self.properties[key] = PropertyValue(value)

    def _unescape(self, s):
        """Unescape Java properties escape sequences."""
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                next_char = s[i + 1]
                if next_char == 'n':
                    result.append('\n')
                    i += 2
                elif next_char == 'r':
                    result.append('\r')
                    i += 2
                elif next_char == 't':
                    result.append('\t')
                    i += 2
                elif next_char == 'f':
                    result.append('\f')
                    i += 2
                elif next_char == '\\':
                    result.append('\\')
                    i += 2
                elif next_char == 'u' and i + 5 < len(s):
                    # Unicode escape \uXXXX
                    try:
                        code = int(s[i+2:i+6], 16)
                        result.append(chr(code))
                        i += 6
                    except (ValueError, OverflowError):
                        result.append(s[i])
                        i += 1
                else:
                    # For other escaped characters, just use the character itself
                    result.append(next_char)
                    i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)

    def get(self, key, default=None):
        """Get a property value by key."""
        return self.properties.get(key, default)

    def __getitem__(self, key):
        """Allow dictionary-style access."""
        return self.properties[key]

    def __setitem__(self, key, value):
        """Allow dictionary-style assignment."""
        if isinstance(value, PropertyValue):
            self.properties[key] = value
        else:
            self.properties[key] = PropertyValue(value)

    def __contains__(self, key):
        """Support 'in' operator."""
        return key in self.properties

    def items(self):
        """Return items like a dictionary."""
        return self.properties.items()

    def keys(self):
        """Return keys like a dictionary."""
        return self.properties.keys()

    def values(self):
        """Return values like a dictionary."""
        return self.properties.values()


def load_config(path: str) -> Properties:
    configs = Properties()
    with open(path, "rb") as f:
        configs.load(f)

    return configs