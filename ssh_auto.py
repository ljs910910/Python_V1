import paramiko

# ssh 프로그램을 이용한 서버 접속이 가능한 경우, 1번 파일에 서버 리스트, 2번 파일에 명령어를 작성하여 실행
# kth tb 환경이나, 개인 vm에 활용 가능

def ssh_auto():
    f1 = open('ssh_server_list.txt', 'r')
    f2 = open('ssh_command.txt', 'r')
    while True:
        try:
            while True:
                line1 = f1.readline().rstrip()
                if not line1:
                    client.close()
                    f1.close()
                    break
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=line1, port=22, username='root', password='dnjfemz1')
                print(line1)
                while True:
                    line2 = f2.readline().rstrip()
                    if line2 is not None:
                        if not line2:
                            f2.close()
                            break
                    stdin, stdout, stderr = client.exec_command(line2)
                    stdin.close()
                    print(line2)
                f2 = open('ssh_command.txt', 'r')

        except TimeoutError as e:  # 서버 연결 안될 경우 해당 서버는 패스
            print('**' + line1 + '**' ' connection time out, pass !!', e)
            pass; continue

        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print('pass', e)
        break

if __name__ == "__main__":
    ssh_auto()