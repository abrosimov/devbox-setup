function _tide_item_python
    if test -n "$VIRTUAL_ENV"
        if command -q python3
            python3 --version | string match -qr "(?<v>[\d.]+)"
        else
            python --version | string match -qr "(?<v>[\d.]+)"
        end
        _tide_print_item python $tide_python_icon' ' "$v"
    else if path is .python-version Pipfile __init__.py pyproject.toml requirements.txt setup.py
        if command -q python3
            python3 --version | string match -qr "(?<v>[\d.]+)"
        else
            python --version | string match -qr "(?<v>[\d.]+)"
        end
        _tide_print_item python $tide_python_icon' ' $v
    end
end
