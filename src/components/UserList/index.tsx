import c from './index.less';

interface Props {
    userList: string[];
}

export default function UserList({userList}: Props) {
    return <div className={c.listContainer}>{userList.map(user => user)}</div>;
}
