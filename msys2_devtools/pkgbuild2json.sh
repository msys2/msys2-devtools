#!/bin/bash
# Sources a PKGBUILD and outputs a json representation of all variables in it.
# Usage: ./src2json.sh PKGBUILD [prefix1 prefix2...]
# Example Output:
# {
#   "prefix1_name1": "value1",
#   "prefix2_name2": ["element1", "element2", ...]
# }

set -e

escape_json_string() {
    local json_string
    json_string="${1//\\/\\\\}"
    json_string="${json_string//\"/\\\"}"
    json_string="${json_string//$'\n'/\\n}"
    json_string="${json_string//$'\t'/\\t}"
    json_string="${json_string//$'\r'/\\r}"
    echo -n "$json_string"
}

# Given a variable name returns a json value representation of it
get_variable_as_json() {
    local var_name="$1"

    if [[ "$(declare -p "$var_name" 2>/dev/null)" =~ "declare -a" ]]; then
        local -n var_ref="$var_name"
        local elements=""
        for element in "${var_ref[@]}"; do
            local escaped_element
            escaped_element="$(escape_json_string "$element")"
            elements+="\"$escaped_element\","
        done
        elements="${elements%,*}"
        echo "[$elements]"
    else
        local var_value
        local escape_value
        eval "var_value=\$$var_name"
        escape_value="$(escape_json_string "$var_value")"
        echo "\"$escape_value\""
    fi
}

check_prefixes() {
    local variable="$1"
    shift
    for prefix in "$@"; do
        if [[ "$variable" == "$prefix"* ]]; then
            return 0
        fi
    done
    return 1
}

# Given a file name returns a json representation of all variables in it.
# Supports strings and arrays of strings.
get_variables_as_json() {
    set +e
    source "$1"
    set -e
    shift
    local variable_names
    variable_names=$(compgen -v)
    local json=""
    for var in $variable_names; do
        # the main reason we don't just extract all is to make it faster
        # with cygwin bash
        if check_prefixes "$var" "$@"; then
            json+="\"$(escape_json_string "$var")\": $(get_variable_as_json "$var"),"
            continue
        fi
    done
    json="{${json%,*}}"
    echo -n "$json"
}

main() {
    local pkgbuild="$1"
    shift
    get_variables_as_json "$pkgbuild" "$@"
}

main "$@"
