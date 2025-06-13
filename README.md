# Clean Teachers

This script helps manage teacher accounts by comparing XML data from Rayuela (educational management system) with LDAP accounts, allowing administrators to identify and remove accounts that are no longer needed.

## Overview

The script performs the following operations:
1. Reads teacher logins from an XML file (provided by Rayuela)
2. Retrieves teacher information from the LDAP directory
3. Identifies LDAP accounts not present in the XML file
4. Prompts the administrator to confirm deletion for each account
5. For confirmed deletions:
   - Removes the teacher's home directory
   - Removes the teacher from all LDAP groups
   - Deletes the teacher's LDAP account

## Requirements

- Python 3.6 or higher
- `ldap3` module
- XML file containing teacher information from Rayuela

## Usage

```bash
python clean_teachers.py teachers.xml
```

Where `teachers.xml` is the path to the XML file containing the list of current teachers.

## Workflow

1. The script loads teacher logins from the XML file using `get_xml_logins()`
2. It retrieves teacher information from LDAP using `get_ldap_teachers()`
3. It identifies teachers in LDAP that are not present in the XML
4. For each account to be deleted:
   - The administrator is prompted to confirm deletion
   - If confirmed, the script:
     - Deletes the teacher's home directory using `delete_directory()`
     - Removes the teacher's LDAP account using `delete_ldap_user()`

## Configuration

The script uses the following LDAP settings:
- LDAP Server: localhost
- Base DN: dc=instituto,dc=extremadura,dc=es
- Admin User: cn=admin,ou=people,dc=instituto,dc=extremadura,dc=es

To configure LDAP authentication, set the `LDAP_PASSWORD` variable in the script.

## Security Note

It's recommended to avoid hardcoding the LDAP password in the script for production environments. Consider using environment variables or a secure configuration file.

## Functions

- `get_xml_logins(xml_path)`: Extracts teacher logins from XML file
- `get_ldap_teachers()`: Retrieves teacher information from LDAP
- `delete_directory(homedir)`: Deletes a teacher's home directory
- `delete_ldap_user(uid)`: Removes a teacher's LDAP account and group memberships
- `compare(xml_path)`: Main function that compares XML and LDAP data and handles deletions
