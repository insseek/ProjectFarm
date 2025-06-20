import React from 'react';

/**
 * 引入方式
 * import GearInputNumber from 'path/GearInputNumber';
 * 使用方式
 <GearInputNumber
 step={5}
 max={99}
 min={0}
 val={this.state.data.tax}
 text={'%'}
 valChange={this.valChange.bind(this, '个人所得税', 'tax')}
 />
 *
 *
 * */

export default class index extends React.Component {
    constructor() {
        super();
        this.state = {
            val: 0
        }
    }

    componentDidMount() {
        this.setPropsData(this.props)
    }

    setPropsData(props) {
        let val = props.val;
        if (props.max != undefined && val > props.max) {
            val = props.max
        } else if (props.min != undefined && val < props.min) {
            val = props.min
        }
        this.setState({
            val: val
        })
    }

    componentWillReceiveProps(nextProps) {
        if (this.props.val !== nextProps.val && nextProps.val !== '') {
            this.setPropsData(nextProps)
        }
    }

    //使input获取焦点
    onInputFocus() {
        $(this.refs.gear_input_dom).focus();
    }

    //input获取焦点时
    inputOnFocus() {
        $(this.refs.gear_input_border).addClass('on-focues');
        if (this.state.val == 0) {
            this.setState({
                val: ''
            }, function () {
                this.props.valChange(this.state.val)
            })
        } else if (this.props.max && this.state.val > this.props.max) {
            this.setState({
                val: this.props.max
            }, function () {
                this.props.valChange(this.state.val)
            })
        }
    }

    //input失去焦点时
    inputOnBlur() {
        $(this.refs.gear_input_border).removeClass('on-focues');
        if (this.state.val == '') {
            this.setState({
                val: 0
            }, function () {
                this.props.valChange(this.state.val)
            })
        } else if (this.props.max && this.state.val > this.props.max) {
            this.setState({
                val: this.props.max
            }, function () {
                this.props.valChange(this.state.val)
            })
        }
    }

    //input输入时
    inputOnInput(e) {
        //数字或者带小数点的数字
        let numberValue = $(e.target).val();
        let reg = /^(0|([1-9]\d*))(\.)?(\d*)?$/;
        if (this.props.max != undefined && numberValue > this.props.max) {
            console.log("this.props.max", this.props.max);
            this.setState({
                val: this.props.max
            }, function () {
                this.props.valChange(this.props.max)
            })
        } else if (this.props.min != undefined && numberValue < this.props.min) {
            this.setState({
                val: this.props.min
            }, function () {
                this.props.valChange(this.state.val)
            })
        } else if (numberValue === '0') {
            this.setState({
                val: 0
            }, function () {
                this.props.valChange(this.state.val)
            })
        } else if (numberValue.trim() === '') {
            this.setState({
                val: ''
            }, function () {
                this.props.valChange(this.state.val)
            })
        } else if (reg.test(numberValue)) {
            this.setState({
                val: numberValue
            }, function () {
                this.props.valChange(this.state.val)
            })
        }
    }


    //上步进
    clickUp() {
        let val = Number(this.state.val) + Number(this.props.step);
        if (this.props.max != undefined && val > this.props.max) {
            val = this.props.max
        }
        this.setState({
            val: val
        }, function () {
            this.props.valChange(this.state.val)
        })
    }

    //下步进
    clickDown() {
        let val = Number(this.state.val) - Number(this.props.step);
        if (this.props.min != undefined && this.state.val < this.props.min) {
            val = this.props.min
        } else if (val < 0) {
            val = 0
        }
        this.setState({
            val: val
        }, function () {
            this.props.valChange(this.state.val)
        })
    }

    render() {
        return (
            <div className='geat-input-num-div'>
                <div ref='gear_input_border' className='input-border'></div>
                <div className='input-num-div'>
                    <div className='input-div'>
                        <input
                            placeholder='请输入'
                            value={this.state.val}
                            type="text"
                            ref='gear_input_dom'
                            onFocus={this.inputOnFocus.bind(this)}
                            onBlur={this.inputOnBlur.bind(this)}
                            onChange={this.inputOnInput.bind(this)}
                            onInput={this.inputOnInput.bind(this)}
                        />
                    </div>
                    <div
                        className={this.props.text && this.props.text.length >= 3 ? 'flag-text long-flag-text' : 'flag-text'}
                        onClick={this.onInputFocus.bind(this)}>{this.props.text}</div>
                    <div className='input-btn-group'>
                        <div className='input-btn input-btn-up' onClick={this.clickUp.bind(this)}>
                            <span></span>
                        </div>
                        <div className='input-btn input-btn-down' onClick={this.clickDown.bind(this)}>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>
        )
    }
}