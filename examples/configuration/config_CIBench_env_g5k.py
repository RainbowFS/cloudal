from cloudal.utils import get_logger, execute_cmd
from cloudal.action import performing_actions_g5k
from cloudal.provisioning.g5k_provisioner import g5k_provisioner
from cloudal.configuring.docker_configurator import docker_configurator

from execo_g5k import oardel


logger = get_logger()


class config_CIbench_env_g5k(performing_actions_g5k):
    """
    """
    def __init__(self):
        super(config_CIbench_env_g5k, self).__init__()

    def provisioning(self):
        logger.info("Init provisioner: g5k_provisioner")
        self.provisioner = g5k_provisioner(config_file_path=self.args.config_file_path,
                                           keep_alive=self.args.keep_alive,
                                           out_of_chart=self.args.out_of_chart,
                                           oar_job_ids=self.args.oar_job_ids)

        self.provisioner.make_reservation()

        """Retrieve the hosts address list and (ip, mac) list from a list of oar_result and
        return the resources which is a dict needed by g5k_provisioner """
        self.provisioner.get_resources()
        self.hosts = self.provisioner.hosts

        if not self.args.no_deploy_os:
            self.provisioner.setup_hosts()

    def config_host(self):
        logger.info("Init Docker configurator")
        configurator = docker_configurator(self.hosts)
        # Install & config Docker
        logger.info("Start configuring Docker on hosts")
        configurator.config_hosts()

        logger.info("Pull AntidoteDB docker image")
        cmd = 'docker pull antidotedb/antidote'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'docker pull google/cadvisor'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install docker-compose")
        cmd = 'apt-get update && apt-get install --yes --allow-change-held-packages --no-install-recommends docker-compose'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        logger.info("Install CI-Bench")
        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/antidote.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/antidote && make docker-build'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/ && git clone https://github.com/AntidoteDB/CI-bench.git'
        self.error_hosts = execute_cmd(cmd, self.hosts)

        cmd = 'cd ~/CI-bench && docker build --no-cache -t antidote-benchmark .'
        self.error_hosts = execute_cmd(cmd, self.hosts)


    def run(self):
        logger.info("Starting provision nodes")
        self.provisioning()
        logger.info("Provisioning nodes: DONE")

        logger.info("Starting configure CI-Bench on nodes")
        self.config_host()
        logger.info("Configuring CI-Bench on nodes: DONE")


if __name__ == "__main__":
    logger.info("Init engine in %s" % __file__)
    engine = config_CIbench_env_g5k()

    try:
        logger.info("Start engine in %s" % __file__)
        engine.start()
    except Exception as e:
        logger.error('Program is terminated by the following exception: %s' % e, exc_info=True)
    except KeyboardInterrupt:
        logger.info('Program is terminated by keyboard interrupt.')

    if not engine.args.keep_alive:
        logger.info('Deleting reservation')
        oardel(engine.provisioner.oar_result)
        logger.info('Reservation deleted')
    else:
        logger.info('Reserved nodes are kept alive for inspection purpose.')
