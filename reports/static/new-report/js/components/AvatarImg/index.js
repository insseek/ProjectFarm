import React from 'react';
import './index.scss';

/** 头像组件
 * 图片加载失败就显示默认图片
 * import Img from 'path/AvatarImg';
 * <AvatarImg imgUrl={} style={}  text={} size={}  bgColor={}/>
 * imgUrl 图片地址
 * style 自定义样式
 * text 文字 与 imgUrl 仅传一个
 * size 大小 默认为20*20   传递数字参数为 size * size
 * bgColor 背景颜色
 *
 */
export default class Index extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            imgUrl: '',  //this.props.imgUrl
        };
    }
    componentDidMount() {
        this.setState({
            imgUrl:this.props.imgUrl
        })

    }
    componentWillReceiveProps (nextProps) {
        if( nextProps.imgUrl && nextProps.imgUrl!='' ){
            this.setState({
                imgUrl:nextProps.imgUrl
            })
        }else{
            this.setState({
                imgUrl:nextProps.imgUrl
            })
        }
    }

    handleImageLoaded() {

    }

    handleImageErrored() {
        this.setState({
            imgUrl: this.props.defUrl
        });
    }

    render() {
        let doms = ''
        if(this.props.text && this.props.text!='' && (!this.state.imgUrl || this.state.imgUrl=='')){
            doms = this.props.text.substring(0,1);
        }else{
            doms = (
                <div>
                    <img
                        src={this.state.imgUrl}
                        onLoad={this.handleImageLoaded.bind(this)}
                        onError={this.handleImageErrored.bind(this)}
                    />
                </div>
            )
        }

        //大小
        let size = '';
        if(this.props.size && this.props.size!=''){
            size = {
                width : this.props.size+'px',
                height : this.props.size+'px',
                lineHeight : this.props.size+'px',
            }
        }
        //背景颜色
        let bgColor = '';
        if(this.props.bgColor && this.props.bgColor!='' && (!this.state.imgUrl || this.state.imgUrl=='')){
            bgColor = {
                backgroundColor : this.props.bgColor,
            }
        }

        return (
            <span className='m-span' style={Object.assign({},this.props.style, size,bgColor)} >
                <div className='m-border'></div>
                {doms}
            </span>
        );
    }
}


Index.propTypes = {
};

Index.defaultProps = {
    defUrl: '/static/new-report/img/default_avatar_img.svg',
    style:{
    }
};