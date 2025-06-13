import xml.etree.ElementTree as ET
import sys
import os
import shutil
import ldap3

LDAP_PASSWORD = ''

def get_xml_logins(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    logins = set()
    for profesor in root.findall('profesor'):
        datos_usuario = profesor.find('datos-usuario-rayuela')
        if datos_usuario is not None:
            login = datos_usuario.findtext('login')
            if login:
                logins.add(login.strip())
    return logins

def get_ldap_teachers():
    profesores_ldap = {}
    
    server = ldap3.Server('localhost')
    
    try:
        with ldap3.Connection(server, auto_bind=True) as conn:
            conn.search(
                'ou=People,dc=instituto,dc=extremadura,dc=es',
                '(uid=*)',
                attributes=['uid', 'homeDirectory', 'cn', 'givenName', 'sn']
            )
            
            for entry in conn.entries:
                uid = str(entry.uid) if hasattr(entry, 'uid') else None
                homedir = str(entry.homeDirectory) if hasattr(entry, 'homeDirectory') else None
                
                nombre = str(entry.givenName) if hasattr(entry, 'givenName') else ""
                apellidos = str(entry.sn) if hasattr(entry, 'sn') else ""
                nombre_completo = str(entry.cn) if hasattr(entry, 'cn') else f"{nombre} {apellidos}".strip()
                
                if uid and homedir and homedir.startswith('/home/profesor'):
                    profesores_ldap[uid] = {
                        'homedir': homedir,
                        'nombre': nombre_completo
                    }
            
    except Exception as e:
        print(f"Error al conectar con LDAP: {e}")
    
    return profesores_ldap

def delete_directory(homedir):
    try:
        if os.path.exists(homedir):
            shutil.rmtree(homedir)
            return True, f"Directorio {homedir} borrado correctamente"
        else:
            return False, f"El directorio {homedir} no existe"
    except Exception as e:
        return False, f"Error al borrar el directorio {homedir}: {str(e)}"

def delete_ldap_user(uid):
    try:
        server = ldap3.Server('localhost')
        
        admin_user = 'cn=admin,ou=people,dc=instituto,dc=extremadura,dc=es'
        base_dn = 'dc=instituto,dc=extremadura,dc=es'
        user_dn = f'uid={uid},ou=People,{base_dn}'
        
        print(f"Iniciando borrado de usuario LDAP para: {uid}")
        print(f"Conectando a LDAP como: {admin_user}")
        
        try:
            conn = ldap3.Connection(
                server, 
                user=admin_user, 
                password=LDAP_PASSWORD,
                auto_bind=True
            )
            print("✅ Conexión a LDAP establecida correctamente")
        except Exception as e:
            print(f"❌ Error de conexión a LDAP: {e}")
            return False, f"Error de conexión a LDAP: {e}"
        
        conn.search('ou=People,' + base_dn, f'(uid={uid})', attributes=['*'])
        if len(conn.entries) == 0:
            print(f"⚠️ Usuario {uid} no encontrado en LDAP")
            return False, f"Usuario {uid} no encontrado en LDAP"
        else:
            print(f"✅ Usuario {uid} encontrado en LDAP")
        
        print(f"Buscando grupos para el usuario {uid}...")
        conn.search(
            'ou=Group,' + base_dn,
            f'(|(memberUid={uid})(member={user_dn}))',
            attributes=['cn']
        )
        grupos = [str(entry.cn) for entry in conn.entries]
        print(f"Grupos encontrados: {grupos}")
        
        for grupo in grupos:
            print(f"Eliminando usuario {uid} del grupo: {grupo}")
            grupo_dn = f'cn={grupo},ou=Group,{base_dn}'
            
            try:
                conn.modify(
                    grupo_dn,
                    {'memberUid': [(ldap3.MODIFY_DELETE, [uid])]}
                )
                print(f"  - memberUid eliminado: {conn.result}")
            except Exception as e:
                print(f"  - Error al eliminar memberUid: {e}")
            
            try:
                conn.modify(
                    grupo_dn,
                    {'member': [(ldap3.MODIFY_DELETE, [user_dn])]}
                )
                print(f"  - member eliminado: {conn.result}")
            except Exception as e:
                print(f"  - Error al eliminar member: {e}")
        
        grupo_personal_dn = f'cn={uid},ou=Group,{base_dn}'
        conn.search('ou=Group,' + base_dn, f'(cn={uid})')
        if conn.entries:
            print(f"Eliminando grupo personal: {grupo_personal_dn}")
            result = conn.delete(grupo_personal_dn)
            print(f"Resultado eliminación grupo personal: {conn.result}")
        
        print(f"Eliminando usuario: {user_dn}")
        result = conn.delete(user_dn)
        if result:
            print(f"✅ Usuario {uid} eliminado correctamente: {conn.result}")
        else:
            print(f"❌ Error al eliminar usuario: {conn.result}")
            return False, f"Error al eliminar usuario: {conn.result['description']}"
        
        conn.search('ou=People,' + base_dn, f'(uid={uid})')
        if len(conn.entries) > 0:
            print(f"❌ The user {uid} still exists after deletion")
            return False, f"The user {uid} still exists after deletion"
        
        print(f"✅ Complete deletion for user {uid}")
        return True, f"User {uid} successfully deleted"
        
    except Exception as e:
        print(f"❌ General error in the deletion process: {e}")
        return False, f"General error in the deletion process: {str(e)}"

def compare(xml_path):
    xml_logins = get_xml_logins(xml_path)
    ldap_teachers = get_ldap_teachers()

    missing_in_xml = set(ldap_teachers.keys()) - xml_logins
    if missing_in_xml:       
        print("\nYou are about to proceed with individual user deletion.")
        print("For each user, you will be asked if you want to delete them.")
        
        for uid in missing_in_xml:
            info = ldap_teachers[uid]
            answer = input(f"\nDo you want to delete teacher {uid} ({info['nombre']})? (y/n): ")
            
            if answer.lower() == 'y':
                home_dir = info['homedir']
                
                dir_success, dir_message = delete_directory(home_dir)
                
                ldap_success, ldap_message = delete_ldap_user(uid)
                
                if dir_success and ldap_success:
                    print(f"  {uid}: User and directory successfully deleted")
                else:
                    print(f"  {uid}: {info['nombre']} - {dir_message}")
                    print(f"     LDAP: {ldap_message}")
            else:
                print(f"  Teacher {uid} ({info['nombre']}) not deleted.")
    else:
        print("\n✅ All teachers in LDAP are in the XML.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python clean_teachers.py teachers.xml")
    else:
        compare(sys.argv[1])
